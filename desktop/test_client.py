"""Launcher ownership and credential-free user-unit arguments."""
import os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from desktop import client
class ClientTests(unittest.TestCase):
    def test_managed_start_survives_launcher_without_forwarding_api_secrets(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(client,'directory',return_value=Path(folder)),patch.object(client,'call',side_effect=[OSError('not started'),{}]),patch.object(client.shutil,'which',return_value='/usr/bin/systemd-run'),patch.object(client.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run,patch.object(client.subprocess,'Popen') as popen,patch.dict(os.environ,{'DEEPSEEK_API_KEY':'do-not-forward'}):
            client.ensure_service();args=run.call_args.args[0];self.assertIn('--user',args);self.assertIn('--collect',args);self.assertTrue(any(x.startswith('--unit=deepseek-lab-') for x in args));self.assertFalse(any('do-not-forward' in x for x in args));popen.assert_not_called()
    def test_unmanaged_platform_retains_detached_fallback(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(client,'directory',return_value=Path(folder)),patch.object(client,'call',side_effect=[OSError('not started'),{}]),patch.object(client.shutil,'which',return_value=None),patch.object(client.subprocess,'Popen') as popen:
            client.ensure_service();self.assertTrue(popen.call_args.kwargs['start_new_session']);self.assertTrue(popen.call_args.kwargs['close_fds'])
    def test_restart_waits_for_old_unit_collection_then_starts_once(self):
        starts=0;probes=0
        def run(args,**kwargs):
            nonlocal starts,probes
            if args[0]=='systemd-run':starts+=1;return SimpleNamespace(returncode=1 if starts==1 else 0)
            probes+=1;return SimpleNamespace(returncode=0 if probes==1 else 3)
        def call(*args):
            if starts<2:raise OSError('old socket is closed')
            return {}
        with tempfile.TemporaryDirectory() as folder,patch.object(client,'directory',return_value=Path(folder)),patch.object(client,'call',side_effect=call),patch.object(client.shutil,'which',return_value='/usr/bin/systemd-run'),patch.object(client.subprocess,'run',side_effect=run),patch.object(client.subprocess,'Popen') as popen,patch.object(client.time,'sleep'):
            client.ensure_service();self.assertEqual(starts,2);popen.assert_not_called()
