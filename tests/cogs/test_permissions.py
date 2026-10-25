from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import yaml

from redbot.cogs.permissions.permissions import Permissions, GLOBAL


def _yaml_attachment(rules):
    async def save(fp):
        fp.write(yaml.safe_dump(rules).encode())
        fp.seek(0)

    return SimpleNamespace(save=save)


@pytest.mark.parametrize("category", ["COG", "COMMAND"])
@pytest.mark.parametrize(
    "rules,error_level",
    [
        ([], "names"),
        ({False: {}}, "names"),
        ({"target": []}, "ids"),
        ({"target": {"defalt": False}}, "ids"),
        ({"target": {123: 100}}, "values"),
        ({"target": {123: None}}, "values"),
        ({"target": {"default": "true"}}, "values"),
    ],
)
async def test_acl_upload_reports_nested_schema_error(red, category, rules, error_level):
    cog = Permissions(red)
    cog._clear_rules = AsyncMock()
    attachment = _yaml_attachment({category: rules})
    ctx = SimpleNamespace(message=SimpleNamespace(attachments=[attachment]), send=AsyncMock())

    await cog._permissions_acl_set(ctx, guild_id=GLOBAL, update=False)

    if error_level == "names":
        error = (
            "Keys under `COG` must be cog names (strings)."
            if category == "COG"
            else "Keys under `COMMAND` must be command names (strings)."
        )
    elif error_level == "ids":
        error = (
            "Keys under cog names must be IDs or `default`."
            if category == "COG"
            else "Keys under command names must be IDs (numbers) or `default`."
        )
    else:
        error = "Rules must be either `true` or `false`."
    ctx.send.assert_awaited_once_with("Your YAML file did not match the schema: " + error)
    cog._clear_rules.assert_not_awaited()


async def test_acl_upload_reports_invalid_top_level_key(red):
    cog = Permissions(red)
    attachment = _yaml_attachment({"INVALID": {}})
    ctx = SimpleNamespace(message=SimpleNamespace(attachments=[attachment]), send=AsyncMock())

    await cog._permissions_acl_set(ctx, guild_id=GLOBAL, update=False)

    ctx.send.assert_awaited_once_with(
        "Your YAML file did not match the schema: "
        "Top-level keys must be either `COG` or `COMMAND`."
    )


def test_schema_update():
    old = {
        str(GLOBAL): {
            "owner_models": {
                "cogs": {
                    "Admin": {"allow": [78631113035100160], "deny": [96733288462286848]},
                    "Audio": {"allow": [133049272517001216], "default": "deny"},
                },
                "commands": {
                    "cleanup bot": {"allow": [78631113035100160], "default": "deny"},
                    "ping": {
                        "allow": [96733288462286848],
                        "deny": [96733288462286848],
                        "default": "allow",
                    },
                },
            }
        },
        "43733288462286848": {
            "owner_models": {
                "cogs": {
                    "Admin": {
                        "allow": [24231113035100160],
                        "deny": [35533288462286848, 24231113035100160],
                    },
                    "General": {"allow": [133049272517001216], "default": "deny"},
                },
                "commands": {
                    "cleanup bot": {"allow": [17831113035100160], "default": "allow"},
                    "set adminrole": {
                        "allow": [87733288462286848],
                        "deny": [95433288462286848],
                        "default": "allow",
                    },
                },
            }
        },
    }
    new = Permissions._get_updated_schema(old)
    assert new == (
        {
            "Admin": {
                str(GLOBAL): {"78631113035100160": True, "96733288462286848": False},
                "43733288462286848": {"24231113035100160": True, "35533288462286848": False},
            },
            "Audio": {str(GLOBAL): {"133049272517001216": True, "default": False}},
            "General": {"43733288462286848": {"133049272517001216": True, "default": False}},
        },
        {
            "cleanup bot": {
                str(GLOBAL): {"78631113035100160": True, "default": False},
                "43733288462286848": {"17831113035100160": True, "default": True},
            },
            "ping": {str(GLOBAL): {"96733288462286848": True, "default": True}},
            "set adminrole": {
                "43733288462286848": {
                    "87733288462286848": True,
                    "95433288462286848": False,
                    "default": True,
                }
            },
        },
    )
