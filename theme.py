CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
 
:root {
  --bg: #070B14; --panel: #0E1626; --panel2: #131E33; --line: #1F2B45;
  --text: #F1F5FB; --muted: #93A1BC; --amber: #FFC21A; --green: #34D399;
  --red: #F87171; --blue: #60A5FA;
}
.stApp { background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, sans-serif; }
.stMarkdown, label, button, input, textarea { font-family: 'Inter', system-ui, sans-serif; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1rem; padding-bottom: 3rem; max-width: 1280px; }
h1, h2, h3, h4 { color: var(--text); letter-spacing: -0.01em; }
 
/* Panels (st.container with border) */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
}
 
/* Buttons */
button[kind="primary"], button[data-testid="stBaseButton-primary"],
div[data-testid="stFormSubmitButton"] > button {
  background: var(--amber); color: #111827; border: 0; border-radius: 10px;
  font-weight: 700; width: 100%;
}
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover { background: #FFD24D; color: #111827; }
button[kind="secondary"], button[data-testid="stBaseButton-secondary"] {
  background: var(--panel2); color: var(--text); border: 1px solid var(--line);
  border-radius: 10px; font-weight: 600; width: 100%;
}
button[kind="secondary"]:hover, button[data-testid="stBaseButton-secondary"]:hover {
  border-color: #3A4D78; color: #fff;
}
div.stDownloadButton > button { background: var(--panel2); color: var(--text); border: 1px solid var(--line); border-radius: 10px; }
 
/* Radio groups used as navigation, day tabs and filters */
div[data-testid="stRadio"] div[role="radiogroup"] { gap: 6px; flex-wrap: wrap; }
div[data-testid="stRadio"] div[role="radiogroup"] > label {
  background: transparent; border: 1px solid transparent; border-radius: 10px;
  padding: 7px 14px; margin: 0; cursor: pointer;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child { display: none; }
div[data-testid="stRadio"] div[role="radiogroup"] > label p { color: #C3CEE3; font-weight: 600; font-size: 14px; margin: 0; }
div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
  background: var(--panel2); border-color: #2B3B5E;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) p { color: var(--amber); }
 
/* Brand and top bar */
.brand { font-size: 23px; font-weight: 800; color: var(--text); display: flex; align-items: center; gap: 10px; }
.brand-ico { width: 38px; height: 38px; border-radius: 10px; border: 1px solid #5A4A1A; background: #1A1608;
             display: inline-flex; align-items: center; justify-content: center; color: var(--amber); }
.brand b { color: var(--amber); font-weight: 800; }
.active-pill { border: 1px solid var(--line); background: var(--panel); border-radius: 10px;
               padding: 9px 14px; font-size: 13px; color: var(--muted); white-space: nowrap;
               overflow: hidden; text-overflow: ellipsis; }
.active-pill b { color: var(--text); font-weight: 600; }
.divider { border-top: 1px solid var(--line); margin: 6px 0 18px 0; }
 
/* Headings */
.eyebrow { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--amber);
           letter-spacing: 0.06em; margin-bottom: 6px; }
.h1 { font-size: 38px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; color: #fff; margin-bottom: 8px; }
.lead { color: var(--muted); font-size: 16px; line-height: 1.55; max-width: 720px; margin-bottom: 18px; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); }
.panel-head { display: flex; justify-content: space-between; align-items: center; gap: 10px;
              font-weight: 700; font-size: 17px; color: #fff; margin-bottom: 12px; }
.panel-head span { font-weight: 400; font-size: 13px; color: var(--muted); }
.live { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--green);
        margin-right: 8px; box-shadow: 0 0 8px var(--green); }
 
/* Destination cards with photos */
.dest { background: var(--panel2); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; margin-bottom: 8px; }
.dest.sel { border-color: var(--amber); box-shadow: 0 0 0 1px var(--amber); }
.dest-ph { height: 150px; position: relative; background-size: cover; background-position: center;
           background-image: linear-gradient(135deg, #16305A, #0B5D5C); }
.match { position: absolute; top: 10px; right: 10px; background: rgba(5, 80, 60, 0.9); color: #6EF3C5;
         border-radius: 6px; padding: 3px 8px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; }
.dest-name { position: absolute; left: 12px; bottom: 10px; right: 12px; font-size: 17px; font-weight: 800; color: #fff;
             text-shadow: 0 1px 6px rgba(0,0,0,0.7); }
.dest-body { padding: 12px 14px; }
.dest-desc { font-size: 13px; color: var(--muted); line-height: 1.5; min-height: 58px; }
.dest-foot { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--line);
             font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--text); }
 
/* Live trip canvas hero */
.canvas-ph { height: 170px; border-radius: 12px; position: relative; margin-bottom: 12px; border: 1px solid var(--line);
             background-size: cover; background-position: center; background-image: linear-gradient(135deg, #16305A, #0B5D5C); }
.canvas-txt { position: absolute; left: 14px; right: 14px; bottom: 12px; }
.canvas-name { font-size: 24px; font-weight: 800; color: #fff; text-shadow: 0 1px 6px rgba(0,0,0,0.7); }
.canvas-sub { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #E5ECF8; text-shadow: 0 1px 6px rgba(0,0,0,0.7); }
 
/* Summary strip */
.strip { display: grid; grid-template-columns: repeat(4, 1fr); background: var(--panel); border: 1px solid var(--line);
         border-radius: 14px; margin-bottom: 18px; }
.strip .cell { padding: 16px 20px; border-right: 1px solid var(--line); }
.strip .cell:last-child { border-right: 0; }
.strip .label { font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.strip .value { font-size: 24px; font-weight: 800; color: #fff; }
.strip .value.good { color: var(--green); font-family: 'JetBrains Mono', monospace; font-size: 21px; }
.strip .value.bad { color: var(--red); font-family: 'JetBrains Mono', monospace; font-size: 21px; }
.strip .sub { font-size: 12px; color: var(--muted); margin-top: 2px; }
 
/* Day header and items */
.dayhead { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 16px 20px; margin: 6px 0 14px 0; }
.dayhead .t { font-size: 20px; font-weight: 800; color: #fff; }
.dayhead .s { font-size: 14px; color: var(--muted); margin-top: 4px; }
.item { display: flex; gap: 16px; align-items: center; background: var(--panel); border: 1px solid var(--line);
        border-radius: 14px; padding: 14px 18px; margin-bottom: 12px; }
.ico { width: 48px; height: 48px; flex-shrink: 0; border-radius: 12px; background: #11284A; color: var(--blue);
       display: flex; align-items: center; justify-content: center; font-size: 22px; }
.thumb { width: 92px; height: 68px; flex-shrink: 0; border-radius: 10px; background-size: cover; background-position: center;
         background-image: linear-gradient(135deg, #16305A, #0B5D5C); }
.item .body { flex: 1; min-width: 0; }
.item .t { font-size: 16px; font-weight: 700; color: #fff; }
.item .s { font-size: 13px; color: var(--muted); margin-top: 3px; }
.item .cost { text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 600; color: #fff; white-space: nowrap; }
.item .cost span { display: block; font-size: 11px; font-weight: 400; color: var(--muted); margin-top: 3px; }
.badge { display: inline-block; margin-left: 8px; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;
         background: #3A2E08; color: var(--amber); vertical-align: middle; }
 
/* Budget bars */
.bar-row { margin-bottom: 14px; }
.bar-top { display: flex; justify-content: space-between; font-size: 14px; color: var(--text); margin-bottom: 5px; }
.bar-top span:last-child { font-family: 'JetBrains Mono', monospace; }
.bar-track { height: 9px; background: #1A2640; border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; }
.gauge-note { font-size: 13px; color: var(--muted); margin-top: 6px; }
 
/* Pills */
.pill { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.pill.ok { background: #0B3B2D; color: #6EF3C5; }
.pill.warn { background: #3A2E08; color: var(--amber); }
.pill.bad { background: #4A1620; color: #FCA5A5; }
.pill.info { background: #11284A; color: #93C5FD; }
 
/* Booking cards and disruption alert */
.bk { background: var(--panel2); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; margin-bottom: 12px; }
.bk.active { border-color: var(--amber); }
.bk-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.bk-title { font-size: 18px; font-weight: 700; color: #fff; }
.bk-sub { font-size: 13px; color: var(--muted); margin-top: 4px; }
.alert { background: linear-gradient(180deg, #2A0F1B, #170B14); border: 1px solid #5A1F32; border-radius: 16px; padding: 20px 22px; margin: 12px 0; }
.alert-top { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.alert-top .mono { color: #FCA5A5; font-weight: 600; letter-spacing: 0.05em; }
.alert-title { font-size: 21px; font-weight: 800; color: #fff; margin-bottom: 6px; }
.alert-text { font-size: 14px; color: #D3B7C0; line-height: 1.5; }
.impact { background: #0D0A12; border: 1px solid #3A2030; border-radius: 12px; padding: 14px 16px; margin-top: 14px; font-size: 14px; color: #D3B7C0; }
.impact b { color: #fff; }
.res-title { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); letter-spacing: 0.05em; margin: 14px 0 8px 0; }
 
/* Empty state */
.empty { background: var(--panel); border: 1px dashed #2B3B5E; border-radius: 16px; padding: 34px; text-align: center; color: var(--muted); }
.empty b { display: block; color: #fff; font-size: 19px; margin-bottom: 6px; }
 
@media (max-width: 800px) {
  .strip { grid-template-columns: repeat(2, 1fr); }
  .strip .cell:nth-child(2) { border-right: 0; }
  .strip .cell:nth-child(-n+2) { border-bottom: 1px solid var(--line); }
  .h1 { font-size: 28px; }
  .item { flex-wrap: wrap; }
  .item .cost { text-align: left; }
}
</style>
"""
 
