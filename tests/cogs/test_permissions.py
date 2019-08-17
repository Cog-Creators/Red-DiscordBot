from redbot.cogs.permissions.permissions import Permissions, GLOBAL


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
