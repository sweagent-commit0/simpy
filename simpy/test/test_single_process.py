# encoding: utf-8
"""
API tests for single processes (no interaction with other processes or
resources).

"""
# Pytest gets the parameters "sim" and "log" from the *conftest.py* file
import pytest


def test_discrete_time_steps(sim, log):
    """Simple simulation with discrete time steps."""
    def pem(context, log):
        while True:
            log.append(context.now)
            yield context.hold(delta_t=1)

    sim.start(pem, log)
    sim.simulate(until=3)

    assert log == [0, 1, 2]


def test_stop_self(sim, log):
    """Process stops itself."""
    def pem(context, log):
        while context.now < 2:
            log.append(context.now)
            yield context.hold(1)

    sim.start(pem, log)
    sim.simulate(10)

    assert log == [0, 1]


def test_start_at(sim):
    def pem(context):
        assert context.now == 5
        yield context.hold(1)

    sim.start(pem(sim.context), at=5)
    sim.simulate()


def test_start_at_error(sim):
    def pem(context):
        yield context.hold(2)

    sim.start(pem(sim.context))
    sim.simulate()
    pytest.raises(ValueError, sim.start, pem(sim.context), at=1)


def test_start_delayed(sim):
    def pem(context):
        assert context.now == 5
        yield context.hold(1)

    sim.start(pem(sim.context), delay=5)
    sim.simulate()


def test_start_delayed_error(sim):
    """Check if delayed() raises an error if you pass a negative dt."""
    def pem(context):
        yield context.hold(1)

    pytest.raises(ValueError, sim.start, pem(sim.context), delay=-1)


def test_start_at_delay_precedence(sim):
    """The ``delay`` param shoul take precedence ofer the ``at`` param."""
    def pem(context):
        assert context.now == 5
        yield context.hold(1)

    sim.start(pem(sim.context), at=3, delay=5)
    sim.simulate()


def test_start_non_process(sim):
    """Check that you cannot start a normal function."""
    def foo():
        pass

    pytest.raises(ValueError, sim.start, foo)


def test_negative_hold(sim):
    """Don't allow negative hold times."""
    def pem(context):
        yield context.hold(-1)

    sim.start(pem)
    pytest.raises(ValueError, sim.simulate)


def test_yield_none_forbidden(sim):
    """A process may not yield ``None``."""
    def pem(context):
        yield

    sim.start(pem)
    pytest.raises(ValueError, sim.simulate)


def test_hold_not_yielded(sim):
    """Check if an error is raised if you forget to yield a hold."""
    def pem(context):
        context.hold(1)
        yield context.hold(1)

    sim.start(pem)
    pytest.raises(RuntimeError, sim.simulate)


def test_illegal_yield(sim):
    """There should be an error if a process neither yields an event
    nor another process."""
    def pem(context):
        yield 'ohai'

    sim.start(pem)
    pytest.raises(ValueError, sim.simulate)


def test_get_process_state(sim):
    """A process is alive until it's generator has not terminated."""
    def pem_a(context):
        yield context.hold(3)

    def pem_b(context, pem_a):
        yield context.hold(1)
        assert pem_a.is_alive

        yield context.hold(3)
        assert not pem_a.is_alive

    proc_a = sim.start(pem_a)
    sim.start(pem_b, proc_a)
    sim.simulate()


def test_simulate_negative_until(sim):
    """TEst passing a negative time to simulate."""
    pytest.raises(ValueError, sim.simulate, -3)


def test_hold_value(sim):
    """You can pass an additional *value* to *hold* which will be
    directly yielded back into the PEM. This is useful to implement some
    kinds of resources or other additions.

    See :class:`simpy.resources.Store` for an example.

    """
    def pem(context):
        val = yield context.hold(1, 'ohai')
        assert val == 'ohai'

    sim.start(pem)
    sim.simulate()
