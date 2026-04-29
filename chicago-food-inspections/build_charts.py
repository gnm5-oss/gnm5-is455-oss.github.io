"""
build_charts.py — Generates standalone interactive HTML chart files.
Run after build_data.py.
Reads CSVs from data/, writes HTML files to charts/.
Run from: projects/chicago-food-inspections/
"""
import os
import json
import pandas as pd
import altair as alt

alt.data_transformers.disable_max_rows()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, 'data')
CHARTS_DIR = os.path.join(SCRIPT_DIR, 'charts')
os.makedirs(CHARTS_DIR, exist_ok=True)

def data_path(f): return os.path.join(DATA_DIR, f)
def chart_path(f): return os.path.join(CHARTS_DIR, f)

driver_data      = pd.read_csv(data_path('driver_data.csv'))
yearly_pass      = pd.read_csv(data_path('yearly_pass.csv'))
before_after     = pd.read_csv(data_path('before_after.csv'))
pictograph_df    = pd.read_csv(data_path('pictograph_first_inspection.csv'))
active_uninsp    = pd.read_csv(data_path('active_uninspected.csv'))
zip_coverage     = pd.read_csv(data_path('zip_coverage.csv'))
uninspected_dots = pd.read_csv(data_path('uninspected_dots.csv'))

FACILITY_ORDER = [
    'Restaurant', 'Grocery Store', 'School', "Children's Services Facility",
    'Bakery', 'Daycare Above and Under 2 Years', 'Daycare (2 - 6 Years)', 'Long Term Care'
]
FACILITY_RANGE = [
    '#4E79A7', '#F28E2B', '#59A14F', '#E15759',
    '#76B7B2', '#EDC948', '#B07AA1', '#FF9DA7'
]
FACILITY_COLOR_MAP = dict(zip(FACILITY_ORDER, FACILITY_RANGE))
YEAR_DOMAIN = ['2010','2011','2012','2013','2014','2015','2016','2017',
               '2018','2019','2020','2021','2022','2023','2024','2025']

BACKGROUND   = '#FAFAF7'
GRID_COLOR   = '#E8E6E0'
AXIS_COLOR   = '#555'
TITLE_COLOR  = '#2c3e50'
SUBTITLE_CLR = '#888'
ACCENT_RED   = '#c0392b'


def theme(chart, title=None, subtitle=None, fs=15, sfs=11, height=None):
    props = {}
    if height:
        props['height'] = height
    if title or subtitle:
        props['title'] = alt.TitleParams(
            text=title or '', subtitle=subtitle or '',
            fontSize=fs, subtitleFontSize=sfs,
            subtitleColor=SUBTITLE_CLR,
            anchor='start', color=TITLE_COLOR, offset=15,
        )
    if props:
        chart = chart.properties(**props)
    return (
        chart
        .configure_view(fill=BACKGROUND, stroke=None)
        .configure_title(fontSize=fs, subtitleFontSize=sfs,
                         subtitleColor=SUBTITLE_CLR,
                         anchor='start', color=TITLE_COLOR)
        .configure_axis(labelFontSize=11, titleFontSize=12,
                        titleFontWeight='bold',
                        labelColor=AXIS_COLOR, titleColor=AXIS_COLOR,
                        gridColor=GRID_COLOR, tickColor=GRID_COLOR,
                        domainColor='#ccc')
        .configure_legend(labelFontSize=11, titleFontSize=12,
                          labelColor=AXIS_COLOR, titleColor=TITLE_COLOR,
                          symbolStrokeWidth=3, padding=8, cornerRadius=4,
                          fillColor='#fff', strokeColor='#e8e6e0')
    )


# ============================================================
# CHART 1 — Interactive line chart with PILLS + year filter
# ============================================================
yearly_pass['Year'] = yearly_pass['Year'].astype(str)
yearly_pass_records = yearly_pass.to_dict(orient='records')

CHART1_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * { box-sizing: border-box; }
  body { margin:0; padding:0; font-family:Arial,sans-serif; background:#FAFAF7; color:#111; }

  .chart-title { font-family:Georgia,serif; font-size:1.25rem; font-weight:bold; color:#2c3e50; margin:0 0 0.2rem; }
  .chart-subtitle { font-family:Arial,sans-serif; font-size:0.8rem; color:#888; margin:0 0 1rem; }

  .controls { display:flex; flex-wrap:wrap; gap:1rem; align-items:flex-end; margin-bottom:0.6rem; }
  .ctrl-group { display:flex; flex-direction:column; gap:0.35rem; }
  .ctrl-label { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#666; }

  .pill-row { display:flex; flex-wrap:wrap; gap:0.35rem; }
  .pill {
    border:2px solid; border-radius:20px; padding:0.22rem 0.7rem;
    font-size:0.75rem; cursor:pointer; background:white;
    transition:background 0.15s, color 0.15s;
    font-family:Arial,sans-serif; white-space:nowrap;
  }
  .pill.on { color:#fff !important; }

  .year-row { display:flex; align-items:center; gap:0.5rem; }
  .year-input {
    width:66px; padding:0.37rem 0.4rem; border:1.5px solid #ccc;
    border-radius:6px; font-size:0.84rem; text-align:center; color:#333;
  }
  .year-sep { color:#aaa; font-size:0.8rem; }

  .reset-btn {
    padding:0.4rem 0.9rem; border:1.5px solid #ddd; border-radius:6px;
    background:#f7f7f7; font-size:0.79rem; cursor:pointer; color:#555;
  }
  .reset-btn:hover { background:#eee; }

  .warn { font-size:0.78rem; color:#c0392b; font-style:italic; min-height:1.1rem; margin-bottom:0.3rem; }

  #vis { width:100%; }
  .vega-embed { width:100% !important; }
  .vega-embed canvas, .vega-embed svg { width:100% !important; }
  .chart-note { font-size:0.75rem; color:#999; font-style:italic; margin-top:0.5rem; }
</style>
</head>
<body>

<p class="chart-title">Pass Rate Across 8 Chicago Facility Types, 2010–2025</p>
<p class="chart-subtitle">Click facility pills to show/hide. Adjust year range to zoom in. Hover any point for details.</p>

<div class="controls">
  <div class="ctrl-group">
    <div class="ctrl-label">Facility Type</div>
    <div class="pill-row" id="pills"></div>
  </div>
  <div class="ctrl-group">
    <div class="ctrl-label">Year Range</div>
    <div class="year-row">
      <input type="number" id="yr-from" class="year-input" value="2010" min="2010" max="2025">
      <span class="year-sep">to</span>
      <input type="number" id="yr-to" class="year-input" value="2025" min="2010" max="2025">
    </div>
  </div>
  <div class="ctrl-group" style="align-self:flex-end">
    <button class="reset-btn" onclick="resetAll()">Reset all</button>
  </div>
</div>

<div class="warn" id="warn-msg"></div>
<div id="vis"></div>
<p class="chart-note">Click a pill to toggle a facility type (min 1). Hover any point for exact values.</p>

<script src="https://cdn.jsdelivr.net/npm/vega@5/build/vega.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5/build/vega-lite.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6/build/vega-embed.min.js"></script>
<script>
const ALL_DATA   = __DATA__;
const FAC_COLORS = __COLORS__;
const ALL_FACS   = __FACS__;
const YEAR_DOM   = __YEARDOMAIN__;

let active   = new Set(ALL_FACS);
let vegaView = null;

const pillRow = document.getElementById('pills');
ALL_FACS.forEach(fac => {
  const btn = document.createElement('button');
  btn.className = 'pill on';
  btn.textContent = fac;
  btn.dataset.fac = fac;
  const col = FAC_COLORS[fac];
  btn.style.borderColor = col;
  btn.style.backgroundColor = col;
  btn.style.color = '#fff';
  btn.addEventListener('click', () => {
    if (active.has(fac) && active.size === 1) {
      showWarn('At least one facility type must remain selected.');
      return;
    }
    clearWarn();
    if (active.has(fac)) {
      active.delete(fac);
      btn.classList.remove('on');
      btn.style.backgroundColor = '#fff';
      btn.style.color = col;
    } else {
      active.add(fac);
      btn.classList.add('on');
      btn.style.backgroundColor = col;
      btn.style.color = '#fff';
    }
    redraw();
  });
  pillRow.appendChild(btn);
});

function resetAll() {
  active = new Set(ALL_FACS);
  document.querySelectorAll('.pill').forEach(btn => {
    const col = FAC_COLORS[btn.dataset.fac];
    btn.classList.add('on');
    btn.style.backgroundColor = col;
    btn.style.color = '#fff';
  });
  document.getElementById('yr-from').value = 2010;
  document.getElementById('yr-to').value   = 2025;
  clearWarn(); redraw();
}

function showWarn(msg) {
  document.getElementById('warn-msg').textContent = msg;
  setTimeout(clearWarn, 2500);
}
function clearWarn() { document.getElementById('warn-msg').textContent = ''; }

document.getElementById('yr-from').addEventListener('change', redraw);
document.getElementById('yr-to').addEventListener('change', redraw);

function filtered() {
  const fy = +document.getElementById('yr-from').value;
  const ty = +document.getElementById('yr-to').value;
  return ALL_DATA.filter(d => active.has(d['Facility Type']) && +d.Year >= fy && +d.Year <= ty);
}

const SPEC = {
  $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
  width: 'container', height: 480,
  data: { name: 'table' },
  params: [{ name: 'xDomain', value: YEAR_DOM }],
  mark: { type:'line', point:{ size:70, filled:true }, strokeWidth:2.5 },
  encoding: {
    x: {
      field:'Year', type:'ordinal', title:'Year',
      scale: { domain: { signal: 'xDomain' } },
      axis:{ labelAngle:-45, titlePadding:12, labelFontSize:11,
             titleFontSize:13, titleFontWeight:'bold', gridColor:'#E8E6E0' }
    },
    y: {
      field:'Pass Rate', type:'quantitative', title:'Pass Rate (%)',
      scale:{ domain:[0,100] },
      axis:{ tickCount:6, labelFontSize:11, titleFontSize:13,
             titleFontWeight:'bold', gridColor:'#E8E6E0' }
    },
    color: {
      field:'Facility Type', type:'nominal',
      scale:{ domain:__DOMAIN__, range:__RANGE__ },
      title:'Facility Type',
      legend:{ orient:'right', offset:10, labelFontSize:11, titleFontSize:12,
               symbolStrokeWidth:3, fillColor:'#fff', strokeColor:'#e8e6e0',
               padding:8, cornerRadius:4 }
    },
    tooltip:[
      { field:'Facility Type', type:'nominal',     title:'Facility Type' },
      { field:'Year',          type:'ordinal',     title:'Year' },
      { field:'Pass Rate',     type:'quantitative',title:'Pass Rate (%)', format:'.1f' },
      { field:'Total',         type:'quantitative',title:'# Inspections', format:',' }
    ]
  },
  config:{ background:'#FAFAF7', view:{ fill:'#FAFAF7', stroke:null }, axis:{ gridColor:'#E8E6E0' } }
};

vegaEmbed('#vis', SPEC, { actions:false, renderer:'svg' })
  .then(r => { vegaView = r.view; redraw(); })
  .catch(console.error);

function redraw() {
  if (!vegaView) return;
  const fy = +document.getElementById('yr-from').value;
  const ty = +document.getElementById('yr-to').value;
  const domainFiltered = YEAR_DOM.filter(y => +y >= fy && +y <= ty);
  vegaView.signal('xDomain', domainFiltered);
  vegaView.change('table', vega.changeset().remove(()=>true).insert(filtered())).run();
}
</script>
</body>
</html>"""

fac_colors_js = json.dumps(FACILITY_COLOR_MAP)
fac_list_js   = json.dumps(FACILITY_ORDER)
domain_js     = json.dumps(FACILITY_ORDER)
range_js      = json.dumps(FACILITY_RANGE)
data_js       = json.dumps(yearly_pass_records)
year_dom_js   = json.dumps(YEAR_DOMAIN)

chart1_html = (
    CHART1_HTML
    .replace('__DATA__',       data_js)
    .replace('__COLORS__',     fac_colors_js)
    .replace('__FACS__',       fac_list_js)
    .replace('__DOMAIN__',     domain_js)
    .replace('__RANGE__',      range_js)
    .replace('__YEARDOMAIN__', year_dom_js)
)
with open(chart_path('main_dashboard.html'), 'w', encoding='utf-8') as f:
    f.write(chart1_html)
print("[OK] main_dashboard.html")


# ============================================================
# CHART 1b — Citywide average overview timeline
# ============================================================
agg = (
    yearly_pass.assign(weighted=yearly_pass['Pass Rate'] * yearly_pass['Total'])
    .groupby('Year', as_index=False)
    .agg(weighted_sum=('weighted','sum'), total_sum=('Total','sum'))
)
agg['Pass Rate'] = agg['weighted_sum'] / agg['total_sum']
agg = agg[['Year', 'Pass Rate']]

overview_line = (
    alt.Chart(agg)
    .mark_line(color=TITLE_COLOR, strokeWidth=3,
               point=alt.OverlayMarkDef(filled=True, size=60, color=TITLE_COLOR))
    .encode(
        x=alt.X('Year:O', title='Year', axis=alt.Axis(labelAngle=-45, titlePadding=12)),
        y=alt.Y('Pass Rate:Q', title='Avg Pass Rate (%)', scale=alt.Scale(domain=[0,100])),
        tooltip=[alt.Tooltip('Year:O'), alt.Tooltip('Pass Rate:Q', format='.1f', title='Avg Pass Rate (%)')]
    )
)
annotations = pd.DataFrame([
    {'Year': '2018', 'label': '2018: New CDPH rules', 'y_pos': 92},
    {'Year': '2020', 'label': '2020: COVID-19',        'y_pos': 78}
])
ann_rules = alt.Chart(annotations).mark_rule(
    color=ACCENT_RED, strokeDash=[4,4], strokeWidth=1.5
).encode(x='Year:O')
ann_text = alt.Chart(annotations).mark_text(
    align='left', dx=6, color=ACCENT_RED, fontSize=11, fontWeight='bold'
).encode(x='Year:O', y=alt.Y('y_pos:Q'), text='label:N')

overview = theme(
    (overview_line + ann_rules + ann_text).properties(width='container', height=220),
    title='Citywide Average Pass Rate (2010–2025)',
    subtitle='Weighted average across all 8 facility types. The 2018 cliff and 2020 COVID dip are clearly visible.',
)
overview.save(chart_path('overview_timeline.html'))
print("[OK] overview_timeline.html")


# ============================================================
# CHART 2 — Dumbbell (2017 vs 2019)
# ============================================================
ba_long = before_after.melt(
    id_vars=['Facility Type','Drop'],
    value_vars=['Pass_2017','Pass_2019'],
    var_name='Year', value_name='Pass Rate'
)
ba_long['Year'] = ba_long['Year'].map({'Pass_2017':'2017','Pass_2019':'2019'})

bars = alt.Chart(before_after).mark_bar(height=3, color=GRID_COLOR).encode(
    y=alt.Y('Facility Type:N', sort=alt.SortField('Drop', order='descending'), title=None),
    x=alt.X('Pass_2019:Q', title='Pass Rate (%)', scale=alt.Scale(domain=[0,100])),
    x2='Pass_2017:Q'
)
dots = alt.Chart(ba_long).mark_circle(size=200, opacity=1).encode(
    y=alt.Y('Facility Type:N', sort=alt.SortField('Drop', order='descending'), title=None),
    x=alt.X('Pass Rate:Q'),
    color=alt.Color('Year:N',
                    scale=alt.Scale(domain=['2017','2019'], range=['#27ae60', ACCENT_RED]),
                    legend=alt.Legend(title='Year', orient='top')),
    tooltip=['Facility Type:N','Year:N',
             alt.Tooltip('Pass Rate:Q', format='.1f', title='Pass Rate (%)')]
)
drop_labels = alt.Chart(before_after).mark_text(
    align='left', dx=8, fontSize=11, fontWeight='bold', color=ACCENT_RED
).encode(
    y=alt.Y('Facility Type:N', sort=alt.SortField('Drop', order='descending')),
    x='Pass_2017:Q',
    text=alt.Text('Drop:Q', format='.1f')
)
dumbbell = theme(
    (bars + dots + drop_labels).properties(width='container', height=350),
    title='Two Years, One Rule Change',
    subtitle='Pass rates collapsed between 2017 and 2019. Numbers = percentage-point drop.',
)
dumbbell.save(chart_path('before_after.html'))
print("[OK] before_after.html")


# ============================================================
# CHART 3 — Heatmap
# ============================================================
rect = alt.Chart(yearly_pass).mark_rect(stroke='#fff', strokeWidth=0.8).encode(
    x=alt.X('Year:O', title='Year', axis=alt.Axis(labelAngle=-45)),
    y=alt.Y('Facility Type:N', sort=FACILITY_ORDER, title=None),
    color=alt.Color('Pass Rate:Q',
                    scale=alt.Scale(scheme='redyellowgreen', domain=[0,100]),
                    legend=alt.Legend(title='Pass Rate (%)', orient='right', gradientLength=200)),
    tooltip=[alt.Tooltip('Facility Type:N'),
             alt.Tooltip('Year:O'),
             alt.Tooltip('Pass Rate:Q', format='.1f', title='Pass Rate (%)'),
             alt.Tooltip('Total:Q', format=',', title='Inspections')]
)
text_hm = alt.Chart(yearly_pass).mark_text(fontSize=9.5).encode(
    x='Year:O',
    y=alt.Y('Facility Type:N', sort=FACILITY_ORDER),
    text=alt.Text('Pass Rate:Q', format='.0f'),
    color=alt.condition(
        'datum["Pass Rate"] < 40 || datum["Pass Rate"] > 72',
        alt.value('white'), alt.value('#333')
    )
)
heatmap = theme(
    (rect + text_hm).properties(width='container', height=300),
    title='Where the Failures Concentrated',
    subtitle='Red = low pass rate, green = high. The 2018–2019 column is red across nearly every row.',
)
heatmap.save(chart_path('heatmap.html'))
print("[OK] heatmap.html")


# ============================================================
# CHART 4 — Pictograph (first-inspection outcomes)
# ============================================================
group_order = [
    'All Chicago Food Businesses',
    'Retail Food (restaurants, grocery, bakery)',
    'Mobile Food (trucks & carts)',
    'Wholesale Food',
]
result_palette = alt.Scale(
    domain=['Pass', 'Pass w/ Conditions', 'Fail'],
    range=['#27ae60', '#f39c12', ACCENT_RED]
)
inner = alt.Chart(pictograph_df).mark_point(filled=True, size=110, shape='square').encode(
    x=alt.X('Col:O', axis=None),
    y=alt.Y('Row:O', axis=None, sort='descending'),
    color=alt.Color('Result:N', scale=result_palette,
                    legend=alt.Legend(title=None, orient='top',
                                      labelFontSize=12, symbolSize=130)),
    tooltip=[alt.Tooltip('Group:N', title='Category'),
             alt.Tooltip('Result:N', title='Outcome'),
             alt.Tooltip('N_total:Q', title='Sample size', format=',')]
).properties(width=240, height=180)

pictograph = (
    inner.facet(
        facet=alt.Facet('Group:N', title=None, sort=group_order,
                        header=alt.Header(labelFontSize=13, labelFontWeight='bold',
                                          labelLimit=320, labelPadding=12,
                                          labelColor=TITLE_COLOR)),
        columns=4,
    )
    .resolve_scale(x='shared', y='shared')
    .properties(
        title=alt.TitleParams(
            text='Of Every 100 New Chicago Food Businesses, How Many Pass on Day One?',
            subtitle='Each square = 1% of first-ever inspections. Green = pass, amber = conditions, red = fail.',
            fontSize=15, subtitleFontSize=11, subtitleColor=SUBTITLE_CLR,
            anchor='start', color=TITLE_COLOR,
        )
    )
    .configure_view(stroke=None, fill=BACKGROUND)
    .configure_title(fontSize=15, subtitleFontSize=11, subtitleColor=SUBTITLE_CLR,
                     anchor='start', color=TITLE_COLOR)
    .configure_legend(labelFontSize=12, titleFontSize=12,
                      fillColor='#fff', strokeColor='#e8e6e0', padding=8, cornerRadius=4)
)
pictograph.save(chart_path('pictograph_first_inspection.html'))
print("[OK] pictograph_first_inspection.html")

# ============================================================
# CHART 5 — Active-uninspected bars
# ============================================================
sort_order = (
    active_uninsp.sort_values('Pct Never Inspected', ascending=False)
    ['Display Label'].tolist()
)
active_uninsp['count_label'] = (
    active_uninsp['Never Inspected'].astype(int).astype(str)
    + ' of '
    + active_uninsp['Active Licenses'].astype(int).map('{:,}'.format)
)
uninsp_bars = alt.Chart(active_uninsp).mark_bar(
    color=ACCENT_RED, cornerRadiusTopRight=4, cornerRadiusBottomRight=4
).encode(
    y=alt.Y('Display Label:N', sort=sort_order, title=None,
            axis=alt.Axis(labelLimit=340, labelFontSize=12)),
    x=alt.X('Pct Never Inspected:Q',
            title='% of active mature licenses never inspected',
            scale=alt.Scale(domain=[0,100])),
    tooltip=[
        alt.Tooltip('Display Label:N',       title='Category'),
        alt.Tooltip('Active Licenses:Q',     title='Active licenses',  format=','),
        alt.Tooltip('Never Inspected:Q',     title='Never inspected',  format=','),
        alt.Tooltip('Pct Never Inspected:Q', title='% never inspected',format='.1f'),
    ]
)
count_labels = alt.Chart(active_uninsp).mark_text(
    align='left', dx=7, fontSize=11, color='#444'
).encode(
    y=alt.Y('Display Label:N', sort=sort_order),
    x='Pct Never Inspected:Q',
    text='count_label:N'
)
uninspected_chart = theme(
    alt.layer(uninsp_bars, count_labels).properties(width='container', height=280),
    title="Where Chicago's Inspection Gaps Concentrate",
    subtitle='Share of long-active food licenses (2+ years) never receiving a CDPH inspection.',
)
uninspected_chart.save(chart_path('active_uninspected.html'))
print("[OK] active_uninspected.html")


# ============================================================
# CHART 6 — ZIP map
# ============================================================
GEOJSON_PATH = data_path('chicago_zips.geojson')
with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
    chicago_geo = json.load(f)

print("GeoJSON property keys:", list(chicago_geo['features'][0]['properties'].keys()))

zip_coverage['zip_code'] = zip_coverage['zip_code'].astype(str)
uninspected_dots['latitude']  = pd.to_numeric(uninspected_dots['latitude'],  errors='coerce')
uninspected_dots['longitude'] = pd.to_numeric(uninspected_dots['longitude'], errors='coerce')
uninspected_dots = uninspected_dots.dropna(subset=['latitude','longitude'])

geo_data = alt.Data(values=chicago_geo['features'])

choropleth = alt.Chart(geo_data).mark_geoshape(stroke='white', strokeWidth=0.6).encode(
    color=alt.Color('pct_uninspected:Q',
                    scale=alt.Scale(scheme='reds', domain=[0,10], clamp=True),
                    legend=alt.Legend(title='% never inspected', orient='right',
                                      format='.0f', gradientLength=200)),
    tooltip=[
        alt.Tooltip('properties.ZIP:N',  title='ZIP code'),
        alt.Tooltip('total_active:Q',    title='Active licenses',   format=','),
        alt.Tooltip('uninspected:Q',     title='Never inspected',   format=','),
        alt.Tooltip('pct_uninspected:Q', title='% never inspected', format='.1f'),
    ]
).transform_lookup(
    lookup='properties.ZIP',
    from_=alt.LookupData(zip_coverage, 'zip_code',
                         ['total_active','uninspected','pct_uninspected'])
).project(type='mercator').properties(width='container', height=720)

dots_layer = alt.Chart(uninspected_dots).mark_circle(
    color='#2c3e50', opacity=0.72, size=20, stroke='white', strokeWidth=0.5
).encode(
    longitude='longitude:Q', latitude='latitude:Q',
    tooltip=[alt.Tooltip('zip_code:N', title='ZIP')]
)

map_chart = (
    alt.layer(choropleth, dots_layer)
    .properties(
        title=alt.TitleParams(
            text="Where Chicago's Uninspected Restaurants Live",
            subtitle=("Each dot = long-active retail food business never inspected. "
                      "ZIP fill = share of that ZIP's licenses never inspected."),
            fontSize=15, subtitleFontSize=11,
            anchor='start', color=TITLE_COLOR,
        )
    )
    .configure_view(stroke=None)
    .configure_title(fontSize=15, subtitleFontSize=11,
                     subtitleColor=SUBTITLE_CLR, anchor='start', color=TITLE_COLOR)
    .configure_legend(labelFontSize=11, titleFontSize=12,
                      fillColor='#fff', strokeColor='#e8e6e0', padding=8, cornerRadius=4)
)
map_chart.save(chart_path('chicago_inspection_map.html'))
print("[OK] chicago_inspection_map.html")

print(f"\nDone — all HTML files written to: {CHARTS_DIR}")
