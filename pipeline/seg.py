import numpy as np, cv2, sys
from PIL import Image, ImageOps
from ai_edge_litert.interpreter import Interpreter
it=Interpreter(model_path=__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'models/selfie_segmentation.tflite')); it.allocate_tensors()
ii=it.get_input_details()[0]; oo=it.get_output_details()[0]
print(ii['shape'], oo['shape'])
def mask(img):
    a=np.asarray(img.convert('RGB')).astype(np.float32)/255
    h,w=a.shape[:2]
    # multi-crop: full image + upper square to improve res
    def run(sub):
        x=cv2.resize(sub,(256,256),interpolation=cv2.INTER_AREA)[None]
        it.set_tensor(ii['index'],x.astype(np.float32)); it.invoke()
        return it.get_tensor(oo['index'])[0,:,:,0]
    m=cv2.resize(run(a),(w,h),interpolation=cv2.INTER_CUBIC)
    # refine top square (head/torso) at higher effective res
    s=min(w,h); y0=0
    sub=run(a[y0:y0+s,0:s]); sub=cv2.resize(sub,(s,s),interpolation=cv2.INTER_CUBIC)
    m[y0:y0+s,0:s]=np.maximum(m[y0:y0+s,0:s]*0.3, sub) if False else 0.5*m[y0:y0+s,0:s]+0.5*sub
    m=np.clip(m,0,1)
    # guided-ish refine
    g=cv2.cvtColor((a*255).astype(np.uint8),cv2.COLOR_RGB2GRAY).astype(np.float32)/255
    try:
        m=cv2.ximgproc.guidedFilter(g, m.astype(np.float32), 8, 1e-4)
    except Exception: m=cv2.GaussianBlur(m,(0,0),2)
    m=np.clip((m-0.5)*3+0.5,0,1)
    return m
if __name__=='__main__':
    for src,name in [(sys.argv[i],sys.argv[i+1]) for i in range(1,len(sys.argv),2)]:
        im=ImageOps.exif_transpose(Image.open(src)).convert('RGB')
        m=mask(im)
        Image.fromarray((m*255).astype(np.uint8)).save(f'seg/{name}_m.png')
        im.save(f'seg/{name}.jpg',quality=95)
        prev=np.asarray(im).astype(np.float32); bg=np.zeros_like(prev); bg[...,1]=120
        comp=prev*m[...,None]+bg*(1-m[...,None])
        Image.fromarray(comp.astype(np.uint8)).resize((im.size[0]//4,im.size[1]//4)).save(f'seg/{name}_prev.jpg')
