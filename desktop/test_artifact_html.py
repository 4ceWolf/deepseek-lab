"""Offscreen browser verification of the fixed, offline HTML artifact template."""
import json,tempfile,time,unittest
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtTest import QTest
from desktop.artifact_html import document
from desktop.test_artifacts import chart

class Requests(QWebEngineUrlRequestInterceptor):
    def __init__(self,parent):super().__init__(parent);self.remote=[]
    def interceptRequest(self,info):
        if info.requestUrl().scheme() not in ('file','data','about'):
            self.remote.append(info.requestUrl().toString());info.block(True)
class Page(QWebEnginePage):
    def __init__(self,profile,parent):super().__init__(profile,parent);self.messages=[]
    def javaScriptConsoleMessage(self,level,message,line,source):self.messages.append(message)
class HtmlArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.profile=QWebEngineProfile();self.requests=Requests(self.profile);self.profile.setUrlRequestInterceptor(self.requests);self.view=QWebEngineView();self.page=Page(self.profile,self.view);self.view.setPage(self.page);self.view.resize(1350,1000);self.view.show();self.downloads=[]
        def download(request):
            request.setDownloadDirectory(self.temp.name);self.downloads.append(request);request.accept()
        self.profile.downloadRequested.connect(download)
    def tearDown(self):
        self.view.close();self.page.deleteLater();self.view.deleteLater();QTest.qWait(25);self.app.processEvents();self.profile.deleteLater();QTest.qWait(25);self.temp.cleanup()
    def wait(self,predicate):
        end=time.monotonic()+8
        while time.monotonic()<end:
            self.app.processEvents()
            if predicate():return
            QTest.qWait(20)
        self.fail('Offscreen HTML check timed out; console: '+repr(self.page.messages))
    def js(self,expression):
        result=[];self.page.runJavaScript(expression,lambda value:result.append(value));self.wait(lambda:bool(result));return result[0]
    def load(self,spec):
        path=Path(self.temp.name)/'artifact.html';path.write_text(document(spec));loaded=[];self.view.loadFinished.connect(loaded.append);self.view.load(QUrl.fromLocalFile(str(path)));self.wait(lambda:bool(loaded));self.assertTrue(loaded[-1]);self.wait(lambda:self.js('document.querySelectorAll("input[type=color]").length')>0)
    def test_live_color_matching_and_offline_template(self):
        self.load(chart());self.assertEqual(self.js('document.querySelectorAll("input[type=color]").length'),12)
        self.js('const palette=document.querySelectorAll("input[type=color]")[6];palette.value="#ee9966";palette.dispatchEvent(new Event("input"));')
        self.assertEqual(self.js('document.querySelector("rect[data-color-index]").getAttribute("fill")'),'#ee9966')
        self.assertEqual(self.js('document.querySelector("text[data-color-index]").getAttribute("fill")'),'#ee9966')
        self.js('document.getElementById("json-save").click()');self.wait(lambda:(Path(self.temp.name)/'artifact.json').exists());self.assertEqual(json.loads((Path(self.temp.name)/'artifact.json').read_text())['style']['palette'][0],'#ee9966')
        self.js('document.getElementById("svg-save").click()');self.wait(lambda:(Path(self.temp.name)/'artifact.svg').exists());self.assertIn('#ee9966',(Path(self.temp.name)/'artifact.svg').read_text())
        self.js('const match=document.getElementById("match");match.checked=false;match.dispatchEvent(new Event("change"));')
        self.assertEqual(self.js('document.querySelector("text[data-color-index]").getAttribute("fill")'),'#b4c4d8')
        self.js('document.getElementById("reset").click()');self.assertEqual(self.js('document.querySelector("rect[data-color-index]").getAttribute("fill")'),'#92baff')
        self.assertEqual(self.requests.remote,[]);self.assertFalse(any('Content Security Policy' in m or 'Refused to execute' in m for m in self.page.messages),self.page.messages)
        previews=Path(__file__).resolve().parents[1]/'build/previews';previews.mkdir(parents=True,exist_ok=True);self.assertTrue(self.view.grab().save(str(previews/'desktop-html-artifact.png')))
        self.view.resize(390,844);QTest.qWait(60);self.assertTrue(self.js('document.documentElement.scrollWidth <= window.innerWidth + 1'))
    def test_model_text_cannot_inject_script(self):
        spec=chart();spec['title']='<script>window.injected=true</script>';spec['source']='</script><script>window.injected=true</script>';self.load(spec)
        self.assertFalse(self.js('Boolean(window.injected)'));self.assertEqual(self.js('document.scripts.length'),2);self.assertIn('<script>',self.js('document.querySelector("h1").textContent'))
        self.assertEqual(self.requests.remote,[])
if __name__=='__main__':unittest.main()
