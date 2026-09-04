import asyncio, os, tempfile, unittest
from pathlib import Path
from codex_control.adapters.codex.version_probe import *
from codex_control.adapters.codex.capabilities import SUPPORTED_CODEX_VERSION

class FakeProcess:
    def __init__(self,out=b"codex-cli 0.144.6\n",code=0,hang=False):
        self.stdout=asyncio.StreamReader(); self.stdout.feed_data(out); self.stdout.feed_eof(); self.stderr=asyncio.StreamReader(); self.stderr.feed_data(b"private stderr"); self.stderr.feed_eof(); self.returncode=None; self.code=code; self.hang=hang; self.terminated=self.killed=0
    async def wait(self):
        if self.hang: await asyncio.Event().wait()
        self.returncode=self.code; return self.code
    def terminate(self): self.terminated+=1
    def kill(self): self.killed+=1
class ProbeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fd,self.path=tempfile.mkstemp(); os.close(fd); os.chmod(self.path,0o755); self.calls=[]
    async def asyncTearDown(self): os.unlink(self.path)
    def probe(self,process,**kwargs):
        async def factory(argv,env,limit): self.calls.append((argv,env,limit)); return process
        return CodexVersionProbe(self.path,parent_environment={"PATH":"/bin","OPENAI_API_KEY":"secret","CODEX_HOME":"/bad"},process_factory=factory,**kwargs)
    async def test_valid_fixed_exec_and_secret_filter(self):
        self.assertEqual(await self.probe(FakeProcess()).probe(),SUPPORTED_CODEX_VERSION); argv,env,_=self.calls[0]; self.assertEqual(argv,[self.path,"--version"]); self.assertEqual(env,{"PATH":"/bin"}); self.assertNotIn("CODEX_HOME",env)
    async def test_invalid_paths(self):
        with self.assertRaises(VersionProbeError): await CodexVersionProbe("codex").probe()
        with self.assertRaises(VersionProbeError): await CodexVersionProbe("/missing/codex").probe()
        os.chmod(self.path,0o644)
        with self.assertRaises(VersionProbeError): await self.probe(FakeProcess()).probe()
    async def test_parse_failures_and_oversize(self):
        for output in (b"wrong 0.144.6\n",b"codex-cli 1.x\n",b"codex-cli 0.144.6\nother\n"):
            with self.assertRaises(VersionProbeError): await self.probe(FakeProcess(output)).probe()
        with self.assertRaises(VersionProbeError): await self.probe(FakeProcess(b"x"*20),stdout_limit=10).probe()
    async def test_nonzero_timeout_and_unsupported(self):
        with self.assertRaises(VersionProbeError): await self.probe(FakeProcess(code=2)).probe()
        process=FakeProcess(hang=True)
        with self.assertRaises(VersionProbeError): await self.probe(process,timeout=.01,cleanup_timeout=.01).probe()
        self.assertGreaterEqual(process.terminated,1)
        self.assertEqual(parse_version_stdout(b"codex-cli 0.144.7\n"),"0.144.7")
    async def test_exact_supported_version_selects_manifest(self):
        manifest=await probe_supported_manifest(self.probe(FakeProcess()))
        self.assertEqual(manifest.codex_cli_version,SUPPORTED_CODEX_VERSION)
        with self.assertRaises(VersionProbeError) as raised:
            await probe_supported_manifest(self.probe(FakeProcess(b"codex-cli 0.144.7\n")))
        self.assertEqual(raised.exception.category,"unsupported_codex_version")
