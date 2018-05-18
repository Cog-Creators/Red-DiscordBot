import io
import yaml
import pathlib
import discord


def yaml_template() -> dict:
    template_fp = pathlib.Path(__file__).parent / "template.yaml"

    with template_fp.open() as f:
        return yaml.safe_load(f)


async def yamlset_acl(ctx, *, config, update):
    _fp = io.BytesIO()
    await ctx.message.attachments[0].save(_fp)

    try:
        data = yaml.safe_load(_fp)
    except yaml.YAMLError:
        _fp.close()
        del _fp
        raise

    old_data = async config()

    for outer, inner in data.items():
        for ok, iv in inner.items():
            for k, v in iv.items():
                if k == "default":
                    data[outer][ok][k] = {"allow": True, "deny": False}.get(v.lower(), None)

                if not update:
                    continue
                try:
                    if isinstance(old_data[outer][ok][k], list):
                        data[outer][ok][k].extend(old_data[outer][ok][k])
                except KeyError:
                    pass

    await config.set(data)


async def yamlget_acl(ctx, *, config):
    data = await config()
    removals = []

    for outer, inner in data.items():
        for ok, iv in inner.items():
            for k, v in iv.items():
                if k != "default":
                    continue
                if v is True:
                    data[outer][ok][k] = "allow"
                elif v is False:
                    data[outer][ok][k] = "deny"
                else:
                    removals.append((outer, ok, k, v))

    for tup in removals:
        o, i, k = tup
        data[o][i].pop(k, None)

    _fp = io.BytesIO(yaml.dump(data, default_flow_style=False).encode())
    _fp.seek(0)
    await ctx.send(file=discord.File(_fp, filename="acl.yaml"))
    _fp.close()
