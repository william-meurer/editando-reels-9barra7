"""Retoque natural da foto da thumb: separação de frequência leve na pele (tira manchinha, mantém textura) e um pouco de luz no rosto."""
import sys, cv2, numpy as np
src, dst = sys.argv[1:3]
img = cv2.imread(src).astype(np.float32); H, W = img.shape[:2]
g = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_BGR2GRAY)
fc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
x, y, w, h = sorted(fc.detectMultiScale(g, 1.1, 6, minSize=(200, 200)), key=lambda r: -r[2])[0]
cx, cy = x + w / 2, y + h / 2
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
d = ((xx - cx) / (w * 0.5)) ** 2 + ((yy - cy - h * 0.05) / (h * 0.66)) ** 2
pele = np.clip((1.2 - d) / 0.5, 0, 1)[..., None]
# baixa frequência (tom) suavizada, alta frequência (poro, cílio) mantida
baixa = cv2.GaussianBlur(img, (0, 0), 6); alta = img - baixa
baixa_lisa = cv2.bilateralFilter(baixa.astype(np.uint8), 0, 12, 10).astype(np.float32)
baixa_lisa = cv2.GaussianBlur(baixa_lisa, (0, 0), 4)
out = img * (1 - 0.45 * pele) + (baixa_lisa + alta * 0.9) * 0.45 * pele
# luz suave no rosto, compensa o escurecimento da capa só ali
dl = ((xx - cx) / (w * 2.2)) ** 2 + ((yy - cy - h * 0.3) / (h * 2.5)) ** 2
out = out * (1 + 0.08 * np.clip(1 - dl, 0, 1) ** 2)[..., None]
cv2.imwrite(dst, np.clip(out, 0, 255).astype(np.uint8))
