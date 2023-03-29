import logging
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
import yaml
from _pytest.logging import LogCaptureHandler


def convert_options_to_params(options):
    params = {}
    for option in options:
        params[option.name] = option.value
    return params


def fake_obfuscate(psScript, obfuscation_command):
    return psScript


@contextmanager
def catch_logs(level: int, logger: logging.Logger) -> LogCaptureHandler:
    """Context manager that sets the level for capturing of logs.

    After the end of the 'with' statement the level is restored to its original value.

    :param level: The level.
    :param logger: The logger to update.
    """
    handler = LogCaptureHandler()
    orig_level = logger.level
    logger.setLevel(level)
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.setLevel(orig_level)
        logger.removeHandler(handler)


@pytest.fixture(scope="module")
def host(db, models):
    host = models.Host(name="HOST_1", internal_ip="1.1.1.1")

    db.add(host)

    yield host


# todo can probably have a shared default agent. This is copy/pasted
# in a few test files.
@pytest.fixture(scope="module", autouse=True)
def agent(db, models, host):
    agent = db.query(models.Agent).first()

    if not agent:
        agent = models.Agent(
            name="TEST123",
            session_id="TEST123",
            host_id=host.id,
            hostname=host.name,
            process_id=1,
            delay=1,
            jitter=0.1,
            external_ip="1.1.1.1",
            session_key="qwerty",
            nonce="nonce",
            profile="profile",
            kill_date="killDate",
            working_hours="workingHours",
            lost_limit=60,
            listener="http",
            language="powershell",
            archived=False,
        )
        db.add(agent)
        db.flush()

    yield agent

    db.query(models.AgentTask).filter(
        models.AgentTask.agent_id == agent.session_id
    ).delete()
    db.delete(agent)
    db.delete(host)
    db.commit()


@pytest.fixture(scope="function")
def main_menu_mock():
    main_menu = Mock()
    main_menu.installPath = "empire/server"

    main_menu.obfuscationv2 = Mock()
    obf_conf_mock = MagicMock()
    main_menu.obfuscationv2.get_obfuscation_config = Mock(
        side_effect=lambda x, y: obf_conf_mock
    )
    main_menu.obfuscationv2.obfuscate = Mock(side_effect=fake_obfuscate)
    main_menu.obfuscationv2.obfuscate_keywords = Mock(side_effect=lambda x: x)

    yield main_menu


@pytest.fixture(scope="function")
def module_service(main_menu_mock):
    from empire.server.core.module_service import ModuleService

    yield ModuleService(main_menu_mock)


def test_load_modules(main_menu_mock, models, db):
    """
    This is just meant to be a small smoke test to ensure that the modules
    that come with Empire can be loaded properly at startup and a script can
    be generated with the default values.
    """
    # https://github.com/pytest-dev/pytest/issues/3697
    # caplog not working for some reason.
    from empire.server.core.module_service import ModuleService

    with catch_logs(
        level=logging.INFO, logger=logging.getLogger(ModuleService.__module__)
    ) as handler:
        module_service = ModuleService(main_menu_mock)

        messages = [x.message for x in handler.records if x.levelno >= logging.WARNING]

    if messages:
        pytest.fail("warning messages encountered during testing: {}".format(messages))

    assert len(module_service.modules) > 300
    assert len(db.query(models.Module).all()) > 300

    for key, module in module_service.modules.items():
        if not module.advanced.custom_generate:
            resp, err = module_service._generate_script(
                db, module, convert_options_to_params(module.options), None
            )

            # not gonna bother mocking out the csharp server right now.
            if err != "csharpserver plugin not running":
                # fail if a module fails to generate a script.
                assert (
                    resp is not None and len(resp) > 0
                ), f"No generated script for module {key}"


def test_execute_custom_generate(module_service, agent, db, models):
    file_path = "empire/test/data/modules/test_custom_module.yaml"
    root_path = f"{db.query(models.Config).first().install_path}/modules/"
    path = Path(file_path)
    module_service._load_module(
        db, yaml.safe_load(path.read_text()), root_path, file_path
    )

    execute = module_service.execute_module(
        db,
        agent,
        "empire_test_data_modules_test_custom_module",
        {"Agent": agent.session_id},
        ignore_admin_check=True,
        ignore_language_version_check=True,
    )

    assert execute is not None
    assert execute[0]["data"] == "This is the module code."
