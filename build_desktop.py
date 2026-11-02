"""Create an editable native desktop source bundle. No dependency installation."""
import hashlib,json,py_compile,stat,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def build():
    files=[ROOT/'engine.py',ROOT/'run-desktop.sh',ROOT/'build_desktop.py',ROOT/'install_desktop.py']
    for folder in ('desktop','docs','knowledge'):
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.qss','.md','.json','.txt','.svg'))
    bridge=ROOT/'desktop/web_bridge';provenance=json.loads((bridge/'PROVENANCE.json').read_text())
    for name,expected in provenance['vendor_files'].items():
        asset=bridge/name
        if not asset.is_file() or hashlib.sha256(asset.read_bytes()).hexdigest()!=expected:raise ValueError('Vendored browser library changed: '+name)
        files.append(asset)
    files.extend(p for p in (bridge/'runtime').rglob('*.js') if p.is_file())
    files.extend(p for p in (bridge/'upstream/src').rglob('*.ts') if p.is_file())
    files.extend(bridge/name for name in ('server.mjs','history.mjs','test_history.mjs','test_interactive_export.mjs','build.mjs','test_gateway.mjs','package.json','PROVENANCE.json','upstream/LICENSE','upstream/README.md'))
    files.extend(p for p in (ROOT/'build/previews').glob('desktop-*.png') if p.is_file() and not p.name.startswith('desktop-live-') and p.name not in {'desktop-current.png','desktop-thinking-updated.png'})
    files.extend(p for p in (ROOT/'build/previews').glob('desktop-*.html') if p.is_file())
    files=sorted(set(files))
    for file in files:
        if file.suffix=='.py':py_compile.compile(str(file),doraise=True)
    directory=ROOT/'dist';directory.mkdir(exist_ok=True)
    manifest={'format':'deepseek-native-source-v1','entrypoint':'sh run-desktop.sh','runtime':'Installed Python 3.10+, PySide6, secret-tool on Linux','installed':False,'optional_website_runtime':'Node 22+, system Chrome/Chromium; pinned browser library bundled, no browser download','files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    archive=directory/'deepseek-workspace-native.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        for file in files:
            name='deepseek-workspace/'+str(file.relative_to(ROOT));info=zipfile.ZipInfo(name);info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(stat.S_IFREG|(0o755 if file.name=='run-desktop.sh' else 0o644))<<16
            zipped.writestr(info,file.read_bytes())
        zipped.writestr('deepseek-workspace/BUILD-MANIFEST.json',json.dumps(manifest,indent=2))
    (directory/'BUILD-MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest();(directory/'SHA256SUMS').write_text(digest+'  '+archive.name+'\n')
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        for name,expected in manifest['files'].items():assert hashlib.sha256(zipped.read('deepseek-workspace/'+name)).hexdigest()==expected
        assert not any('/data/' in name or name.endswith('.sqlite3') for name in zipped.namelist())
    return {'archive':str(archive),'sha256':digest,'files':len(files),'bytes':archive.stat().st_size,'installed':False}

if __name__=='__main__':print(json.dumps(build(),indent=2))
