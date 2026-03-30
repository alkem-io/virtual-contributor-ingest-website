class TestEnv:
    def test_default_values(self, monkeypatch):
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("LOCAL_PATH", raising=False)
        monkeypatch.delenv("CHUNK_SIZE", raising=False)
        monkeypatch.delenv("PROCESS_PAGES_LIMIT", raising=False)

        from config import Env
        env = Env()

        assert env.log_level == "INFO"
        assert env.local_path == "./"
        assert env.verbose is False
        assert env.chunk_size == 2000
        assert env.process_pages_limit == 20

    def test_env_var_overrides(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("LOCAL_PATH", "/tmp/test")
        monkeypatch.setenv("CHUNK_SIZE", "5000")
        monkeypatch.setenv("PROCESS_PAGES_LIMIT", "50")

        from config import Env
        env = Env()

        assert env.log_level == "WARNING"
        assert env.local_path == "/tmp/test"
        assert env.chunk_size == 5000
        assert env.process_pages_limit == 50

    def test_verbose_true_when_debug(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        from config import Env
        env = Env()

        assert env.verbose is True

    def test_verbose_false_when_not_debug(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        from config import Env
        env = Env()

        assert env.verbose is False
