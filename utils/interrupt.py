#%%
import os
import signal


class InterruptHandler:
    """
    Convert Ctrl+C (SIGINT) into a graceful-abort request flag instead of an
    immediate KeyboardInterrupt.

    Why this is needed in TCSpy
    ---------------------------
    A terminal Ctrl+C delivers SIGINT to the WHOLE foreground process group:
    the main process, every observation child Process, and every
    multiprocessing.Manager process backing shared_memory. With the default
    handler, children die mid-action (leaving shared_memory['is_running']=True
    and device locks held) and Manager processes die (breaking every
    shared_memory proxy), so a graceful abort becomes impossible.

    This handler is installed in the main process BEFORE any Manager/Process
    is created, so every forked child inherits it. In children the handler is
    a no-op (pid check), making them immune to SIGINT. Only the main process
    sets the `interrupted` flag; the caller then coordinates the shutdown
    through the existing abort_action Event mechanism.

    Usage
    -----
    >>> interrupt = InterruptHandler()
    >>> interrupt.install()          # MUST precede MultiTelescopes()/Manager creation
    >>> ...
    >>> while application.is_running:
    >>>     time.sleep(1)
    >>>     if interrupt.interrupted:
    >>>         application.abort()
    >>>         break
    """

    def __init__(self):
        self.interrupted = False
        self._main_pid = os.getpid()

    def install(self):
        """Install the SIGINT handler. Must be called from the main thread of the main process."""
        signal.signal(signal.SIGINT, self._handler)

    def _handler(self, signum, frame):
        # Forked children (observation processes, Manager servers) inherit this
        # handler; the pid check makes it a no-op there, so they are immune to
        # Ctrl+C and can only be stopped through the abort_action Event.
        if os.getpid() == self._main_pid:
            if not self.interrupted:
                print('\n[SIGINT] Graceful abort requested. Waiting for running actions to stop... (force quit: kill -9)')
            self.interrupted = True
