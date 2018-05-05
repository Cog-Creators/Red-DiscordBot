import io
import yaml
import pathlib
import discord


def yaml_template() -> dict:
    template_fp = pathlib.Path(__file__).parent / 'template.yaml'

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

    to_set = {}
    to_set['cmds'] = data.get('commands', {})
    to_set['cogs'] = data.get('cogs', {})

    for outer, inner in to_set.items():
        for k, v in inner.items():
            if k == 'default':
                to_set[outer][inner][k] = {
                    'allow': True,
                    'deny': False
                }.get(v.lower(), None)

    if update:
        async with config() as cfg:
            cfg.update(to_set)
    else:
        await config.set(to_set)


async def yamlget_acl(ctx, *, config):
    data = await config()
    removals = []

    for outer, inner in data.items():
        for k, v in inner.items():
            if k != 'default':
                continue
            if v is True:
                data[outer][inner][k] = 'allow'
            elif v is False:
                data[outer][inner][k] = 'deny'
            else:
                removals.append((outer, inner, k))

    for tup in removals:
        o, i, k = tup
        data[o][i].pop(k, None)

    _fp = io.BytesIO()

    yaml.dump(data, stream=_fp, default_flow_style=False)
    _fp.seek(0)
    await ctx.send(
        file=discord.File(_fp, filename='acl.yaml')
    )
