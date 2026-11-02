"""Persistent secrets go only through the Linux Secret Service."""
import subprocess

class Credentials:
    attrs=['application','deepseek-workspace','account','default']
    def _call(self,args,value=None):
        try:
            return subprocess.run(['secret-tool']+args,input=value,text=True,capture_output=True,timeout=20)
        except (FileNotFoundError,subprocess.TimeoutExpired):raise RuntimeError('Linux credential store unavailable or locked. Unlock the keyring and try again.') from None
    def load(self):
        result=self._call(['lookup']+self.attrs)
        if result.returncode==0:return result.stdout.strip()
        if result.returncode==1:return ''
        raise RuntimeError('Could not read the credential store. Unlock your keyring.')
    def save(self,key):
        if not isinstance(key,str) or not key.strip() or '\n' in key:raise ValueError('Enter a valid single-line API key')
        result=self._call(['store','--label=DeepSeek Workspace API key']+self.attrs,key.strip())
        if result.returncode:raise RuntimeError('Key was not saved. Unlock the Linux keyring and try again.')
    def remove(self):
        if self._call(['clear']+self.attrs).returncode not in (0,1):raise RuntimeError('Could not remove the saved key')
