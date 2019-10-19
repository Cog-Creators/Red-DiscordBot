import asyncio
import pickle
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Set, Tuple
from weakref import WeakValueDictionary

from ... import data_manager, errors
from .. import IdentifierData, BaseDriverMixin, BaseDriver, BaseDriverABC, ConfigCategory
from .structure import XXHashStorage

_instances = WeakValueDictionary({})

__all__ = ("SplitFilesDriver",)


class DriverSingleton(type):
    """ There should be only one of this driver per cog """

    def __call__(cls, *args, **kwargs):
        if args in _instances:
            return _instances[args]
        temp = super(DriverSingleton, cls).__call__(*args, **kwargs)
        _instances[args] = temp
        return temp


class SplitFilesDriver(BaseDriverMixin, metaclass=DriverSingleton):
    """
    Flat file storage, stored across files, distributing keys using a stable hash
    """

    def __init__(self, cog_name: str, identifier: str):
        self.cog_name = cog_name
        self.unique_cog_identifier = identifier
        if cog_name == "Core" and identifier == "0":
            self.data_path = data_manager.core_data_path()
            bin_count = 1
        else:
            self.data_path = (
                data_manager.cog_data_path(raw_name=cog_name) / "splitfiles" / identifier
            )
            bin_count = 1000  # Consider allowing resizing later on
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.data = XXHashStorage(self.data_path, bin_count)
        self.lock = asyncio.Lock()
        self._block_saves = False  # Don't touch this without a long hard thought.

    # Begin satisfying methods solely for BaseDriver compat
    @classmethod
    async def initialize(cls, **storage_details) -> None:
        """ We don't do anything special here. """
        pass

    @classmethod
    async def teardown(cls) -> None:
        pass

    @staticmethod
    def get_config_details() -> Dict[str, Any]:
        return {}

    # End BaseDriver compat

    @staticmethod
    def keys_plen_from_id_data(identifier_data: IdentifierData) -> Tuple[Tuple[str], int]:
        keys = (
            identifier_data.category,
            *identifier_data.primary_key,
            *identifier_data.identifiers,
        )

        pklen = identifier_data.primary_key_len + 1  # may need other changes on this.
        if identifier_data.category == ConfigCategory.GLOBAL:
            # Because....
            pklen += 1

        return keys, pklen

    async def get(self, identifier_data: IdentifierData):
        keys, pklen = self.keys_plen_from_id_data(identifier_data)
        missing_keys = pklen - len(keys)

        if missing_keys == 0:
            return self.data.get(keys)
        elif missing_keys < 0:
            key, extra_idents = keys[:pklen], keys[:pklen]
            ret = self.data.get(key)
            for ident in extra_idents:
                ret = ret[ident]
            return ret
        # If we're here, we're above the document level and need to collect data.
        # Above the document level for getting is a little slower

        ret = {}

        for key_tuple, inner_value in self.data.iter_by_key_prefix(keys):
            p = ret
            cat, *outer_keys, final_key = key_tuple

            for k in outer_keys:
                p = p.setdefault(k, {})

            p[final_key] = inner_value

        return ret

    async def set(self, identifier_data: IdentifierData, value=None):
        async with self.lock:
            keys, pklen = self.keys_plen_from_id_data(identifier_data)
            changed_bins = self._internal_set(keys, pklen, value)
            await self.save_bins(changed_bins)

    async def clear(self, identifier_data: IdentifierData):
        async with self.lock:
            if identifier_data == IdentifierData(
                self.cog_name, self.unique_cog_identifier, "", (), (), 0
            ):
                # Wiping a whole cog's data,
                # This wont happen frequently, but let's be efficient about it.
                import shutil

                shutil.rmtree(self.data_path)
                self.data_path.mkdir(parents=True, exist_ok=True)
                return
            # Normal casing below

            keys, pklen = self.keys_plen_from_id_data(identifier_data)

            missing_keys_count = pklen - len(keys)
            changed_bins = set()

            if missing_keys_count == 0:
                changed_bins.add(self.data.clear(keys))
            elif missing_keys_count > 0:
                # above doc
                for key_tuple, inner_value in self.data.iter_by_key_prefix(keys):
                    changed_bins.add(self.data.clear(key_tuple))
            else:  # clear inner vals
                pkey, remaining = keys[:pklen], keys[pklen:]
                *other_keys, final_key = remaining
                try:
                    partial = self.data.get(pkey)
                    for k in other_keys:
                        partial = partial[k]
                    del partial[final_key]
                except KeyError:
                    pass
                else:
                    changed_bins.add(self.data.insert(pkey, partial))

            await self.save_bins(changed_bins)

    async def save_bins(self, bins: Optional[Iterable[int]] = None, *, all_bins: bool = False):
        if self._block_saves:
            return
        if all_bins:
            bins = range(self.data._bin_count)
        elif not bins:
            return

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.data.write_bins, *bins)

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        yield "Core", "0"
        for _dir in data_manager.cog_data_path().iterdir():
            data_path = _dir / "splitfiles"
            if not data_path.exists():
                continue
            for inner in data_path.iterdir():
                if inner.is_dir():
                    yield _dir.name, inner.name

    def _internal_set(self, keys, pklen, value) -> Set[int]:

        missing_keys_count = pklen - len(keys)
        changed_bins = set()

        if missing_keys_count > 0:
            # We're above a unique id set here
            for k, v in value.items():
                nkeys = keys + (k,)
                changed_bins |= self._internal_set(nkeys, pklen, v)

        elif missing_keys_count == 0:  # Normal case
            changed_bin = self.data.insert(keys, value)
            changed_bins.add(changed_bin)

        elif missing_keys_count < 0:  # Not missing keys, attribute access
            pkey, ids = keys[:pklen], keys[pklen:]
            try:
                data = self.data.get(pkey)
            except KeyError:
                data = {}

            for ident in ids[:-1]:
                try:
                    partial = partial.setdefault(ident, {})
                except AttributeError:
                    # Bad config use attempting to use a value as a group
                    raise errors.CannotSetSubfield
            else:
                partial = value

            changed_bin = self.data.insert(keys, value)
            changed_bins.add(changed_bin)

        return changed_bins
