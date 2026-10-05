from scripts.autopilot.species.numeric_swarm import NumericSwarm, _study_name_token


def _swarm_with_epoch(epoch_label: str | None, epoch: int = 0) -> NumericSwarm:
    swarm = NumericSwarm.__new__(NumericSwarm)
    swarm.epoch_label = _study_name_token(epoch_label)
    swarm._epoch = epoch
    return swarm


def test_study_name_uses_persistent_instrument_era_label() -> None:
    swarm = _swarm_with_epoch("E5-autopilot-speed")

    assert swarm._study_name("think_harder") == (
        "autopilot_think_harder_era_E5_autopilot_speed"
    )


def test_study_name_keeps_structural_epoch_inside_instrument_era() -> None:
    swarm = _swarm_with_epoch("E5-autopilot-speed", epoch=2)

    assert swarm._study_name("monitor") == (
        "autopilot_monitor_era_E5_autopilot_speed_epoch2"
    )


def test_study_name_token_sanitizes_and_bounds_era_label() -> None:
    assert _study_name_token(" E5/v6+iqk kernel! ") == "E5_v6_iqk_kernel"
    assert len(_study_name_token("x" * 200)) == 80
