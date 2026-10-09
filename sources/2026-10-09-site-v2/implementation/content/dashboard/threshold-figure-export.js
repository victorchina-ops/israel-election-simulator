const INK = '#14273e';
const MUTED = '#5c6c7e';
const COLORS = {a:'#dc454c',b:'#2378cf',other:'#87909d',arab:'#87909d'};
const number = (value, digits = 2) => Number(value).toLocaleString('he-IL', {minimumFractionDigits:digits, maximumFractionDigits:digits});

function rounded(ctx, x, y, width, height, radius, fill) {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
  ctx.fillStyle = fill;
  ctx.fill();
}

function write(ctx, text, x, y, {size=19, weight=400, color=INK, align='right', direction='rtl', maxWidth} = {}) {
  ctx.font = `${weight} ${size}px Arial, sans-serif`;
  ctx.fillStyle = color;
  ctx.textAlign = align;
  ctx.direction = direction;
  ctx.textBaseline = 'middle';
  if (maxWidth) ctx.fillText(String(text), x, y, maxWidth);
  else ctx.fillText(String(text), x, y);
}

async function loadLogo(source) {
  if (!source) return null;
  // Only the application's bundled or same-origin assets may enter the canvas.
  try {
    const url = new URL(source, window.location.href);
    if (!['data:', 'blob:'].includes(url.protocol) && url.origin !== window.location.origin) return null;
    return await new Promise(resolve => {
      const image = new Image();
      image.onload = () => resolve(image.naturalWidth && image.naturalHeight ? image : null);
      image.onerror = () => resolve(null);
      image.src = source;
    });
  } catch { return null; }
}

function meanLabel(party, iterations) {
  if (!Number.isFinite(party?.mean)) return '—';
  const margin = party.meanMargin;
  const valid = iterations > 1 && Number.isFinite(margin) && Array.isArray(party.meanCI) && party.meanCI.every(Number.isFinite);
  const digits = valid && margin > 0 && margin < .005 ? Math.min(6, Math.max(3, Math.ceil(-Math.log10(margin))+1)) : 2;
  return number(party.mean, iterations > 1 ? 2 : 0) + (valid ? ` ± ${number(margin, digits)}` : '');
}

/** Export the displayed reviewed rows, preserving their effective chart order. */
export async function downloadThresholdFigure({rows, parties, iterations, asOf, title='סיכויי המעבר של המפלגות', chart, logoSources={}}) {
  if (!Array.isArray(rows) || !rows.length) throw new Error('אין נתונים ליצוא התרשים.');
  await document.fonts?.ready;
  const effective = chart?.effective || chart || {};
  const options = effective.barOptions || {};
  const style = options.style || {};
  const track = options.track || {};
  const getParty = id => parties instanceof Map ? parties.get(id) : Array.isArray(parties) ? parties.find(party => party.id === id) : parties?.[id];
  const logos = await Promise.all(rows.map(row => loadLogo(logoSources[row.id])));
  const width = 1440, rowHeight = 68, tableTop = 230;
  const height = tableTop + rows.length * rowHeight + (rows[0]?.['קרדיט לשיטה']?194:154);
  const canvas = document.createElement('canvas');
  canvas.width = width * 2;
  canvas.height = height * 2;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('הדפדפן אינו מאפשר יצוא תמונה.');
  ctx.scale(2, 2);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);
  rounded(ctx, 0, 0, width, 12, 0, '#14273e');
  write(ctx, title, 1378, 60, {size:34, weight:700, maxWidth:1310});
  const metadata = [`${Number(iterations || 0).toLocaleString('he-IL')} הרצות`, asOf ? `תאריך נתונים: ${asOf}` : null,rows[0]?.['שיטת שקלול'],rows[0]?.['סקרי ערוץ 14']?`ערוץ 14: ${rows[0]['סקרי ערוץ 14']}`:null].filter(Boolean).join('  ·  ');
  write(ctx, metadata, 1378, 103, {size:18, color:MUTED});
  const featureMetadata=[rows[0]?.['אות ורעש']?`אות ורעש: ${rows[0]['אות ורעש']}`:null,rows[0]?.['דמיון בין סקרים']?`דמיון בין סקרים: ${rows[0]['דמיון בין סקרים']}`:null].filter(Boolean).join('  ·  ');
  write(ctx, featureMetadata, 1378, 133, {size:18, color:MUTED,maxWidth:1310});
  const legend = [{label:'הקואליציה הנוכחית',color:COLORS.a,width:246},{label:'האופוזיציה',color:COLORS.b,width:182},{label:'ללא שיוך לגוש',color:COLORS.other,width:214}];
  let legendX = 1378;
  for (const item of legend) {
    rounded(ctx, legendX - 14, 167, 14, 14, 4, item.color);
    write(ctx, item.label, legendX - 24, 174, {size:17, color:MUTED});
    legendX -= item.width;
  }
  rounded(ctx, 48, tableTop - 28, width - 96, 42, 8, '#f0f4f8');
  write(ctx, 'מפלגה', 1278, tableTop - 7, {size:17, weight:700});
  write(ctx, 'סיכוי מעבר', 968, tableTop - 7, {size:17, weight:700, align:'center'});
  write(ctx, 'תוחלת מנדטים ± 95%', 230, tableTop - 7, {size:17, weight:700, align:'center'});

  rows.forEach((row, index) => {
    const y = tableTop + 48 + index * rowHeight;
    const party = getParty(row.id);
    const color = row[style.colorField || 'צבע הגוש'] || COLORS[party?.bloc || party?.defaultBloc] || COLORS.other;
    const textColor = row[style.textColorField || 'צבע הגוש'] || color;
    const raw = row[effective.y || 'סיכוי מעבר'];
    const value = raw == null ? null : Number(raw);
    const rawMax = typeof track.max === 'string' ? row[track.max] : track.max;
    const max = Number.isFinite(Number(rawMax)) && Number(rawMax) > 0 ? Number(rawMax) : 1;
    const probability = Number.isFinite(value) ? Math.max(0, Math.min(1, value / max)) : null;
    if (index % 2 === 0) rounded(ctx, 48, y - 28, width - 96, 56, 8, '#f8fafc');
    rounded(ctx, 1298, y - 24, 80, 48, 7, row.id === 'israel_first' ? '#172436' : '#ffffff');
    const logo = logos[index];
    if (logo) {
      const ratio = Math.min(70 / logo.naturalWidth, 36 / logo.naturalHeight);
      const logoWidth = logo.naturalWidth * ratio, logoHeight = logo.naturalHeight * ratio;
      ctx.drawImage(logo, 1338 - logoWidth / 2, y - logoHeight / 2, logoWidth, logoHeight);
    }
    write(ctx, row['מפלגה'] || party?.name || row.id, 1278, y, {size:20, weight:700, color:textColor, maxWidth:246});
    write(ctx, probability == null ? '—' : `${number(probability * 100)}%`, 968, y, {size:20, weight:700, color, align:'center', direction:'ltr'});
    const barX = 410, barWidth = 474, barHeight = 16;
    rounded(ctx, barX, y - barHeight / 2, barWidth, barHeight, 8, track.color || '#e8edf2');
    if (probability > 0) {
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(barX, y - barHeight / 2, barWidth, barHeight, 8);
      ctx.clip();
      ctx.fillStyle = color;
      ctx.fillRect(barX + barWidth * (1 - probability), y - barHeight / 2, barWidth * probability, barHeight);
      ctx.restore();
    }
    write(ctx, meanLabel(party, iterations), 230, y, {size:21, weight:700, color, align:'center', direction:'ltr', maxWidth:282});
  });

  const footerY = tableTop + rows.length * rowHeight + 48;
  ctx.strokeStyle = '#dce4ed';
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(48, footerY - 7); ctx.lineTo(width - 48, footerY - 7); ctx.stroke();
  write(ctx, '± מציין רווח סמך 95% לתוחלת מההרצות בלבד; הוא אינו טווח תוצאות הבחירות.', 1378, footerY + 22, {size:18, color:MUTED});
  write(ctx, 'התחזית וסיכויי המעבר מותנים בנתוני הסקרים, בהנחות המודל ובהרכב הגושים שנבחר.', 1378, footerY + 52, {size:18, color:MUTED});
  write(ctx, 'אחוז החסימה: 3.25% מהקולות הכשרים. התוחלת כוללת גם הרצות שבהן המפלגה לא עברה.', 1378, footerY + 82, {size:17, color:MUTED});
  if(rows[0]?.['קרדיט לשיטה'])write(ctx, rows[0]['קרדיט לשיטה']+' · חלון אחוזי מקור: '+rows[0]['חלון אחוזי מקור'], 1378, footerY + 112, {size:17, color:MUTED});

  const blob = await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('יצוא התמונה נכשל.')), 'image/png'));
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'threshold-probabilities.png';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
