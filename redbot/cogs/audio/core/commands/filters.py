import logging
from pathlib import Path

import lavalink
from lavalink import filters
from lavalink.filters import Equalizer
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box
from tabulate import tabulate

from ...converters import (
    ChannelMixConverter,
    DistortionConverter,
    KaraokeConverter,
    LowPassConverter,
    OffConverter,
    RotationConverter,
    TimescaleConverter,
    TremoloConverter,
    VibratoConverter,
)
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Commands.Effects")
_ = Translator("Audio", Path(__file__))


class EffectsCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="effects", invoke_without_command=True)
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def command_effects(self, ctx: commands.Context):
        """Control all affects that can be applied to tracks."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        equalizer = player.equalizer
        karaoke = player.karaoke
        timescale = player.timescale
        tremolo = player.tremolo
        vibrato = player.vibrato
        rotation = player.rotation
        distortion = player.distortion
        low_pass = player.low_pass
        channel_mix = player.channel_mix
        t_effect = _("Effect")
        t_activated = _("State")
        t_yes = _("Activated")
        t_no = _("Deactivated")

        data = [
            {
                t_effect: equalizer.__class__.__name__,
                t_activated: _("Active: {name}").format(name=equalizer.name)
                if equalizer.changed
                else t_no,
            }
        ]

        for effect in (
            karaoke,
            timescale,
            tremolo,
            vibrato,
            rotation,
            distortion,
            low_pass,
            channel_mix,
        ):
            data.append(
                {
                    t_effect: effect.__class__.__name__,
                    t_activated: t_yes if effect.changed else t_no,
                }
            )

        await self.send_embed_msg(
            ctx,
            title=_("Here is the music effects status:"),
            description=box(tabulate(data)),
        )

    @command_effects.command(name="karaoke", usage="off OR <level> <mono> <band> <width>")
    async def command_effects_karaoke(
        self, ctx: commands.Context, *, user_input: KaraokeConverter
    ):
        """
        Eliminate part of a band, usually targeting vocals.
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        karaoke = player.karaoke
        enabled, settings = user_input
        if not enabled:
            karaoke.reset()
        else:
            level, mono, band, width = settings
            karaoke.level = level
            karaoke.mono_level = mono
            karaoke.filter_band = band
            karaoke.filter_width = width
        await player.set_filters(karaoke=karaoke)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="timescale", usage="off OR <speed> <pitch> <rate>")
    async def command_effects_timescale(
        self, ctx: commands.Context, *, user_input: TimescaleConverter
    ):
        """
        Changes the speed, pitch, and rate for tracks.
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        timescale = player.timescale
        enabled, settings = user_input

        if not enabled:
            timescale.reset()
        else:
            speed, pitch, rate = settings
            timescale.speed = speed
            timescale.pitch = pitch
            timescale.rate = rate
            player.low_pass.reset()
        await player.set_filters(
            low_pass=None
            if timescale.changed
            else player.low_pass,  # Timescale breaks if it applied with lowpass
            equalizer=player.equalizer if player.equalizer.changed else None,
            karaoke=player.karaoke if player.karaoke.changed else None,
            tremolo=player.tremolo if player.tremolo.changed else None,
            vibrato=player.vibrato if player.vibrato.changed else None,
            distortion=player.distortion if player.distortion.changed else None,
            timescale=timescale if timescale.changed else None,
            channel_mix=player.channel_mix if player.channel_mix.changed else None,
            volume=player.volume,
            reset_not_set=True,
        )
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="tremolo", usage="off OR <frequency> <depth>")
    async def command_effects_tremolo(
        self, ctx: commands.Context, *, user_input: TremoloConverter
    ):
        """
        Uses amplification to create a shuddering effect, where the volume quickly oscillates.

        Constraints:
        frequency > 0
        depth >0 and <=1
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )
        enabled, settings = user_input

        tremolo = player.tremolo
        if not enabled:
            tremolo.reset()
        else:
            frequency, depth = settings
            try:
                tremolo.frequency = frequency
            except ValueError:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Set Effect"),
                    description=_("Tremolo frequency must be greater than 0."),
                )
            try:
                tremolo.depth = depth
            except ValueError:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Set Effect"),
                    description=_(
                        "Tremolo depth must be greater than 0 and less than or equals to 1."
                    ),
                )
        await player.set_filters(tremolo=tremolo)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="vibrato", usage="off OR <frequency> <depth>")
    async def command_effects_vibrato(
        self, ctx: commands.Context, *, user_input: VibratoConverter
    ):
        """
        Uses amplification to create a shuddering effect, where the pitch quickly oscillates.

        Constraints:
        frequency > 0 and <= 14
        depth >0 and <=1
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )
        enabled, settings = user_input

        vibrato = player.vibrato
        if not enabled:
            vibrato.reset()
        else:
            frequency, depth = settings

            try:
                vibrato.frequency = frequency
            except ValueError:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Set Effect"),
                    description=_(
                        "Vibrato frequency must be greater than 0 and less than or equals to 14."
                    ),
                )
            try:
                vibrato.depth = depth
            except ValueError:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Set Effect"),
                    description=_(
                        "Vibrato depth must be greater than 0 and less than or equals to 1."
                    ),
                )
        await player.set_filters(vibrato=vibrato)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="rotation", usage="off OR <frequency>")
    async def command_effects_rotation(
        self, ctx: commands.Context, *, user_input: RotationConverter
    ):
        """
        Rotates the sound around the stereo channels/user headphone
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )
        enabled, settings = user_input

        rotation = player.rotation
        if enabled:
            rotation.reset()
        else:
            (frequency,) = settings
            rotation.hertz = frequency
        await player.set_filters(rotation=rotation)
        await ctx.invoke(self.command_effects)

    @command_effects.command(
        name="distortion",
        usage="off OR <scale> <offset> <sin-offset> <sin-scale> <cos-scale> <cos-offset> <tan-offset> <tan-scale>",
    )
    async def command_effects_distortion(
        self, ctx: commands.Context, *, user_input: DistortionConverter
    ):
        """Distortion effect. It can generate some pretty unique audio effects."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        distortion = player.distortion
        enabled, settings = user_input

        if not enabled:
            distortion.reset()
        else:
            scale, offset, soffset, sscale, cscale, coffset, toffset, tscale = settings
            distortion.scale = scale
            distortion.offset = offset
            distortion.sin_offset = soffset
            distortion.sin_scale = sscale
            distortion.cos_scale = cscale
            distortion.cos_offset = coffset
            distortion.tan_offset = toffset
            distortion.tan_scale = tscale
        await player.set_filters(distortion=distortion)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="reset", aliases=["off", "disable", "clear", "remove"])
    async def command_effects_reset(self, ctx: commands.Context):
        """Reset all effects."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        player.equalizer.reset()
        player.karaoke.reset()
        player.timescale.reset()
        player.tremolo.reset()
        player.vibrato.reset()
        player.rotation.reset()
        player.distortion.reset()
        player.low_pass.reset()
        player.channel_mix.reset()

        await player.set_filters()
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="bassboost", aliases=["baseboost"], usage="[off]")
    async def command_effects_bassboost(
        self, ctx: commands.Context, *, state: OffConverter = True
    ):
        """This effect emphasizes Punchy Bass and Crisp Mid-High tones.

        Not suitable for tracks with Deep/Low Bass."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        if state:
            eq = Equalizer.boost()
        else:
            eq = player.equalizer
            eq.reset()
        await player.set_filters(equalizer=eq)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="piano", usage="[off]")
    async def command_effects_piano(self, ctx: commands.Context, *, state: OffConverter = True):
        """This effect is suitable for Piano tracks, or tacks with an emphasis on Female Vocals.

        Could also be used as a Bass Cutoff."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effectss."),
            )

        if state:
            eq = Equalizer.piano()
        else:
            eq = player.equalizer
            eq.reset()
        await player.set_filters(equalizer=eq)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="metal", usage="[off]")
    async def command_effects_metal(self, ctx: commands.Context, *, state: OffConverter = True):
        """Experimental Metal/Rock Equalizer.

        Expect clipping on Bassy songs."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        if state:
            eq = Equalizer.metal()
        else:
            eq = player.equalizer
            eq.reset()
        await player.set_filters(equalizer=eq)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="nightcore", usage="[off]")
    async def command_effects_nightcore(
        self, ctx: commands.Context, *, state: OffConverter = True
    ):
        """Apply the nightcore effect."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        if state:
            eq = filters.Equalizer(
                levels=[
                    {"band": 0, "gain": -0.075},
                    {"band": 1, "gain": 0.125},
                    {"band": 2, "gain": 0.125},
                ],
                name="Nightcore",
            )
            ts = filters.Timescale(speed=1.17, pitch=1.2, rate=1)
            player.low_pass.reset()
        else:
            eq = player.equalizer
            ts = player.timescale
            ts.reset()
            eq.reset()
        await player.set_filters(
            low_pass=None,  # Timescale breaks if it applied with lowpass
            equalizer=eq,
            karaoke=player.karaoke if player.karaoke.changed else None,
            tremolo=player.tremolo if player.tremolo.changed else None,
            vibrato=player.vibrato if player.vibrato.changed else None,
            distortion=player.distortion if player.distortion.changed else None,
            timescale=ts,
            channel_mix=player.channel_mix if player.channel_mix.changed else None,
            volume=player.volume,
            reset_not_set=True,
        )
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="vaporwave", usage="[off]")
    async def command_effects_vaporwave(
        self, ctx: commands.Context, *, state: OffConverter = True
    ):
        """Apply the vaporwave effect."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        if state:
            eq = filters.Equalizer(
                levels=[
                    {"band": 0, "gain": -0.075},
                    {"band": 1, "gain": 0.125},
                    {"band": 2, "gain": 0.125},
                ],
                name="Vaporwave",
            )
            ts = filters.Timescale(speed=0.70, pitch=0.75, rate=1)
            tm = filters.Tremolo(frequency=14, depth=0.25)
            player.low_pass.reset()
        else:
            eq = player.equalizer
            ts = player.timescale
            tm = player.tremolo
            ts.reset()
            eq.reset()
            tm.reset()

        await player.set_filters(
            low_pass=None,  # Timescale breaks if it applied with lowpass
            equalizer=eq,
            karaoke=player.karaoke if player.karaoke.changed else None,
            tremolo=tm,
            vibrato=player.vibrato if player.vibrato.changed else None,
            distortion=player.distortion if player.distortion.changed else None,
            timescale=ts,
            channel_mix=player.channel_mix if player.channel_mix.changed else None,
            volume=player.volume,
            reset_not_set=True,
        )
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="synth", usage="[off]")
    async def command_effects_synth(self, ctx: commands.Context, *, state: OffConverter = True):
        """Apply the synth effect."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to apply effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to apply effects."),
            )

        if state:
            eq = filters.Equalizer(
                levels=[
                    {"band": 0, "gain": -0.075},
                    {"band": 1, "gain": 0.325},
                    {"band": 2, "gain": 0.325},
                    {"band": 4, "gain": 0.25},
                    {"band": 5, "gain": 0.25},
                    {"band": 7, "gain": -0.35},
                    {"band": 8, "gain": -0.35},
                    {"band": 11, "gain": 0.8},
                    {"band": 12, "gain": 0.45},
                    {"band": 13, "gain": -0.025},
                ],
                name="Synth",
            )
            ts = filters.Timescale(speed=1.0, pitch=1.1, rate=1.00)
            tm = filters.Tremolo(frequency=4, depth=0.25)
            vb = filters.Vibrato(frequency=11, depth=0.3)
            dt = filters.Distortion(
                sin_offset=0,
                sin_scale=-0.25,
                cos_offset=0,
                cos_scale=-0.5,
                tan_offset=-2.75,
                tan_scale=-0.7,
                offset=-0.27,
                scale=-1.2,
            )
            player.low_pass.reset()
        else:
            eq = player.equalizer
            ts = player.timescale
            tm = player.tremolo
            vb = player.vibrato
            dt = player.distortion
            ts.reset()
            eq.reset()
            tm.reset()
            vb.reset()
            dt.reset()

        await player.set_filters(
            low_pass=None,  # Timescale breaks if it applied with lowpass
            equalizer=eq,
            karaoke=player.karaoke if player.karaoke.changed else None,
            tremolo=tm,
            vibrato=vb,
            distortion=dt,
            timescale=ts,
            channel_mix=player.channel_mix if player.channel_mix.changed else None,
            volume=player.volume,
            reset_not_set=True,
        )
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await ctx.invoke(self.command_effects)

    @command_effects.command(
        name="channelmix",
        usage="off OR <left_to_left> <left_to_right> <right_to_left> <right_to_right>",
    )
    async def command_effects_channelmix(
        self, ctx: commands.Context, *, user_input: ChannelMixConverter
    ):
        """
        Mixes both channels (left and right), with a configurable factor on how much each channel affects the other.
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        channel_mix = player.channel_mix
        enabled, settings = user_input

        if not enabled:
            channel_mix.reset()
        else:
            left_to_left, left_to_right, right_to_left, right_to_right = settings
            channel_mix.left_to_left = left_to_left
            channel_mix.left_to_right = left_to_right
            channel_mix.right_to_left = right_to_left
            channel_mix.right_to_right = right_to_right
        await player.set_filters(channel_mix=channel_mix)
        await ctx.invoke(self.command_effects)

    @command_effects.command(name="lowpass", usage="off OR <smoothing>")
    async def command_effects_lowpass(
        self, ctx: commands.Context, *, user_input: LowPassConverter
    ):
        """
        Higher frequencies get suppressed, while lower frequencies pass through this filter
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to change effects."),
            )
        if dj_enabled and not can_skip and not await self.is_requester_alone(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You need the DJ role to change effects."),
            )

        low_pass = player.low_pass
        enabled, settings = user_input

        if not enabled:
            low_pass.reset()
        else:
            (smoothing,) = settings
            low_pass.smoothing = smoothing
            player.timescale.reset()

        await player.set_filters(
            low_pass=low_pass if low_pass.changed else None,
            equalizer=player.equalizer if player.equalizer.changed else None,
            karaoke=player.karaoke if player.karaoke.changed else None,
            tremolo=player.tremolo if player.tremolo.changed else None,
            vibrato=player.vibrato if player.vibrato.changed else None,
            distortion=player.distortion if player.distortion.changed else None,
            timescale=None  # Timescale breaks if it applied with lowpass
            if low_pass.changed
            else player.timescale,
            channel_mix=player.channel_mix if player.channel_mix.changed else None,
            volume=player.volume,
            reset_not_set=True,
        )
        await ctx.invoke(self.command_effects)
