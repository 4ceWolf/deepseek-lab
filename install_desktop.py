"""User-local editable installation. Does not install system dependencies or start the app."""
import argparse,json,os,shlex,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def install(home=None,source=ROOT):
    home=Path(home or Path.home());source=Path(source).resolve()
    if not (source/'desktop/app.py').is_file():raise ValueError('Native application source is missing')
    bindir=home/'.local/bin';apps=home/'.local/share/applications'
    bindir.mkdir(parents=True,exist_ok=True);apps.mkdir(parents=True,exist_ok=True)
    launcher=bindir/'deepseek-lab';entry=apps/'deepseek-lab.desktop'
    # Persistent state and documentation remain under Projects with the editable app.
    script='#!/bin/sh\n# DeepSeek Lab managed launcher\nset -eu\n'
    script+='export DEEPSEEK_DESKTOP_SOURCE='+shlex.quote(str(source))+'\n'
    script+='export DEEPSEEK_DESKTOP_DATA='+shlex.quote(str(source/'data/desktop'))+'\n'
    script+='cd '+shlex.quote(str(source))+'\nexec /usr/bin/python3 -m desktop.app "$@"\n'
    def desktop_quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')+'"'
    contents='[Desktop Entry]\nType=Application\nVersion=1.0\nName=DeepSeek Lab\nComment=Native DeepSeek chat, coding workspace and ECU controls\n'
    contents+='Exec='+desktop_quote(launcher)+'\nTryExec='+str(launcher)+'\nIcon='+str(source/'desktop/deepseek-lab.svg')+'\n'
    contents+='Terminal=false\nCategories=Development;\nKeywords=DeepSeek;Chat;Coding;ECU;\nStartupNotify=true\nStartupWMClass=deepseek-lab\n'
    for path,text,marker in [(launcher,script,'# DeepSeek Lab managed launcher'),(entry,contents,'Name=DeepSeek Lab')]:
        if path.exists() and marker not in path.read_text():raise ValueError('Existing unmanaged file would be overwritten: '+str(path))
    launcher.write_text(script);launcher.chmod(0o755);entry.write_text(contents);entry.chmod(0o644)
    return dict(name='DeepSeek Lab',source=str(source),launcher=str(launcher),desktop_entry=str(entry),icon=str(source/'desktop/deepseek-lab.svg'),data=str(source/'data/desktop'),editable=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args()
    result=install();print(json.dumps(result,indent=2))
    for command in (['desktop-file-validate',result['desktop_entry']],['update-desktop-database',str(Path(result['desktop_entry']).parent)]):
        try:subprocess.run(command,check=True,capture_output=True,text=True,timeout=15)
        except FileNotFoundError:pass
