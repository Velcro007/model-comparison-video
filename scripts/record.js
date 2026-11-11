// Run through ego-browser nodejs (stdin), after reading the installed ego-browser guide.
// Substitute the configuration object in a working copy; reuse one space for all models.
const cfg = {
  space: 0,
  page: 'p1',
  url: 'http://localhost:8766/scene.html',
  output: '/absolute/output/scene.webm',
  screenshot: '/absolute/output/scene.png',
  seconds: 11,
};
const fs = await import('node:fs/promises');
const task = await taskSpace(cfg.space);
const page = task.page(cfg.page);
await page.goto(cfg.url);
await page.waitForSelector('canvas');
// Only use this for a single canvas scene. Multi-canvas or DOM visuals require
// full-viewport capture; do not omit visible model output silently.
console.log(await page.evaluate(() => ({canvases:document.querySelectorAll('canvas').length,width:innerWidth,height:innerHeight})));
await page.evaluate(({seconds}) => {
  const canvas = document.querySelector('canvas');
  if (!canvas || !canvas.width || !canvas.height) throw new Error('Canvas not ready');
  window.captureDone = false;
  const type = ['video/webm;codecs=vp9','video/webm;codecs=vp8'].find(x => MediaRecorder.isTypeSupported(x));
  if (!type) throw new Error('No supported WebM codec');
  const chunks=[];
  const recorder=new MediaRecorder(canvas.captureStream(30),{mimeType:type,videoBitsPerSecond:12000000});
  recorder.ondataavailable=e=>chunks.push(e.data);
  recorder.onstop=()=>{const reader=new FileReader();reader.onload=()=>{window.captureBase64=reader.result.split(',')[1];window.captureDone=true};reader.readAsDataURL(new Blob(chunks,{type:'video/webm'}));};
  recorder.start();setTimeout(()=>recorder.stop(),seconds*1000);
},{seconds:cfg.seconds});
await page.waitForFunction(()=>window.captureDone,undefined,{timeout:(cfg.seconds+15)*1000});
await fs.writeFile(cfg.output,Buffer.from(await page.evaluate(()=>window.captureBase64),'base64'));
console.log(await page.screenshot({path:cfg.screenshot}));
