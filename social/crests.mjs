// Σήματα σε μονόχρωμο σχέδιο, όπως στα επίσημα γραφικά (Κόμο, ακαδημία ΠΑΟΚ): ό,τι είναι σκούρο ή
// χρωματιστό παίρνει το χρώμα `tone` (λευκό στο πρόγραμμα, μαύρο στα αποτελέσματα), το ανοιχτό φόντο
// γίνεται διάφανο, και κόβεται το κενό γύρω από το σήμα. Τρέχει μέσα στη σελίδα:
//   await page.evaluate(MONO_CRESTS, 255)
export const MONO_CRESTS = async (tone) => {
  await Promise.all([...document.querySelectorAll(".lg img")].map(async (img) => {
    await img.decode().catch(() => {});
    const w = img.naturalWidth, h = img.naturalHeight;
    if (!w) return;
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const x = c.getContext("2d"); x.drawImage(img, 0, 0);
    const d = x.getImageData(0, 0, w, h), p = d.data;
    let x0 = w, y0 = h, x1 = -1, y1 = -1;
    for (let i = 0; i < p.length; i += 4) {
      const lum = (0.299 * p[i] + 0.587 * p[i + 1] + 0.114 * p[i + 2]) / 255;
      const ink = Math.max(0, Math.min(1, (0.88 - lum) / 0.55)) * (p[i + 3] / 255);
      p[i] = p[i + 1] = p[i + 2] = tone; p[i + 3] = Math.round(ink * 255);
      if (p[i + 3] > 24) {
        const px = (i / 4) % w, py = Math.floor(i / 4 / w);
        if (px < x0) x0 = px; if (px > x1) x1 = px; if (py < y0) y0 = py; if (py > y1) y1 = py;
      }
    }
    if (x1 < 0) return;
    x.putImageData(d, 0, 0);
    const t = document.createElement("canvas"); t.width = x1 - x0 + 1; t.height = y1 - y0 + 1;
    t.getContext("2d").drawImage(c, x0, y0, t.width, t.height, 0, 0, t.width, t.height);
    img.src = t.toDataURL();
    await img.decode().catch(() => {});
  }));
};
