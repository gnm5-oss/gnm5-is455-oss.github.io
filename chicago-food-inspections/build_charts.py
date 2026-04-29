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

def data_path(filename):
    return os.path.join(DATA_DIR, filename)

def chart_path(filename):
    return os.path.join(CHARTS_DIR, filename)

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
facility_colors = alt.Scale(domain=FACILITY_ORDER, range=FACILITY_RANGE)

# ============================================================
# CHART 1 — Interactive single line chart with JS controls
# ============================================================
yearly_pass_records = yearly_pass.to_dict(orient='records')

CHART1_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * { box-sizing: border-box; }
  body { margin: 0; padding: 0; font-family: Arial, sans-serif; background: transparent; }
  .controls {
    display: flex; flex-wrap: wrap; gap: 1.25rem;
    padding: 0.75rem 0 1.25rem; align-items: flex-start;
  }
  .ctrl-group { display: flex; flex-direction: column; gap: 0.45rem; }
  .ctrl-label {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #666;
  }
  .pill-row { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .pill {
    border: 2px solid; border-radius: 20px; padding: 0.22rem 0.7rem;
    font-size: 0.75rem; cursor: pointer; background: white;
    transition: background 0.15s, color 0.15s;
    font-family: Arial, sans-serif; white-space: nowrap;
  }
  .pill.on { color: #fff !important; }
  .year-row { display: flex; align-items: center; gap: 0.5rem; }
  .year-input {
    width: 62px; padding: 0.3rem 0.4rem; border: 1px solid #ccc;
    border-radius: 4px; font-size: 0.85rem; text-align: center;
    font-family: Arial, sans-serif;
  }
  .year-sep { color: #888; font-size: 0.82rem; }
  .reset-btn {
    border: 1px solid #ccc; border-radius: 4px; padding: 0.28rem 0.75rem;
    font-size: 0.75rem; cursor: pointer; background: #f5f5f5;
    font-family: Arial, sans-serif; align-self: flex-end;
  }
  .reset-btn:hover { background: #e8e8e8; }
  #vis { width: 100%; }
  .vega-embed { width: 100% !important; }
  .vega-embed canvas, .vega-embed svg { width: 100% !important; }
  .chart-note { font-size: 0.75rem; color: #888; font-style: italic; margin-top: 0.4rem; }
</style>
</head>
<body>

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
  <div class="ctrl-group" style="align-self:flex-end;">
    <button class="reset-btn" onclick="reset()">Reset all</button>
  </div>
</div>

<div id="vis"></div>
<p class="chart-note">Click a facility pill to show/hide it. Hover any point for exact pass rate and inspection count.</p>

<script src="https://cdn.jsdelivr.net/npm/vega@5/build/vega.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5/build/vega-lite.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6/build/vega-embed.min.js"></script>

<script>
const ALL_DATA = __DATA__;
const FAC_COLORS = __COLORS__;
const ALL_FACS = __FACS__;

let active = new Set(ALL_FACS);
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

document.getElementById('yr-from').addEventListener('change', redraw);
document.getElementById('yr-to').addEventListener('change', redraw);

function reset() {
  active = new Set(ALL_FACS);
  document.querySelectorAll('.pill').forEach(btn => {
    const col = FAC_COLORS[btn.dataset.fac];
    btn.classList.add('on');
    btn.style.backgroundColor = col;
    btn.style.color = '#fff';
  });
  document.getElementById('yr-from').value = 2010;
  document.getElementById('yr-to').value = 2025;
  redraw();
}

function filtered() {
  const fy = +document.getElementById('yr-from').value;
  const ty = +document.getElementById('yr-to').value;
  return ALL_DATA.filter(d => active.has(d['Facility Type']) && d.Year >= fy && d.Year <= ty);
}

const SPEC = {
  $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
  width: 'container', height: 390,
  data: { name: 'table' },
  layer: [
    {
      mark: { type: 'line', point: { size: 65, filled: true }, strokeWidth: 2.5 },
      encoding: {
        x: { field: 'Year', type: 'ordinal', title: 'Year',
             axis: { labelAngle: -45, titlePadding: 12, labelFontSize: 11, titleFontSize: 13 } },
        y: { field: 'Pass Rate', type: 'quantitative', title: 'Pass Rate (%)',
             scale: { domain: [0, 100] },
             axis: { tickCount: 6, labelFontSize: 11, titleFontSize: 13, titleFontWeight: 'bold' } },
        color: {
          field: 'Facility Type', type: 'nominal',
          scale: { domain: __DOMAIN__, range: __RANGE__ },
          title: 'Facility Type',
          legend: { orient: 'right', offset: 8, labelFontSize: 11, titleFontSize: 12 }
        },
        tooltip: [
          { field: 'Facility Type', type: 'nominal',      title: 'Facility Type' },
          { field: 'Year',          type: 'ordinal',       title: 'Year' },
          { field: 'Pass Rate',     type: 'quantitative',  title: 'Pass Rate (%)', format: '.1f' },
          { field: 'Total',         type: 'quantitative',  title: '# Inspections', format: ',' }
        ]
      }
    },
    {
      data: { values: [
        { Year: '2018', y: 96, label: '← July 2018: CDPH rule change' },
        { Year: '2020', y: 82, label: '← 2020: COVID-19' }
      ]},
      layer: [
        { mark: { type: 'rule', color: '#c0392b', strokeDash: [5,3], strokeWidth: 1.4 },
          encoding: { x: { field: 'Year', type: 'ordinal' } } },
        { mark: { type: 'text', align: 'left', dx: 4, fontSize: 10, color: '#c0392b', fontStyle: 'italic' },
          encoding: { x: { field: 'Year', type: 'ordinal' },
                      y: { field: 'y', type: 'quantitative', scale: { domain: [0,100] } },
                      text: { field: 'label', type: 'nominal' } } }
      ]
    }
  ],
  config: { view: { fill: '#F7F7F7', stroke: null }, axis: { gridColor: '#E6E6E6' } }
};

vegaEmbed('#vis', SPEC, { actions: false, renderer: 'svg' })
  .then(result => { vegaView = result.view; redraw(); })
  .catch(console.error);

function redraw() {
  if (!vegaView) return;
  vegaView.change('table', vega.changeset().remove(() => true).insert(filtered())).run();
}
</script>
</body>
</html>"""

fac_colors_js = json.dumps(FACILITY_COLOR_MAP)
fac_list_js   = json.dumps(FACILITY_ORDER)
domain_js     = json.dumps(FACILITY_ORDER)
range_js      = json.dumps(FACILITY_RANGE)
data_js       = json.dumps(yearly_pass_records)

chart1_html = (
    CHART1_HTML
    .replace('__DATA__',   data_js)
    .replace('__COLORS__', fac_colors_js)
    .replace('__FACS__',   fac_list_js)
    .replace('__DOMAIN__', domain_js)
    .replace('__RANGE__',  range_js)
)
with open(chart_path('main_dashboard.html'), 'w', encoding='utf-8') as f:
    f.write(chart1_html)
print("[OK] main_dashboard.html")


# ============================================================
# CHART 2 — Dumbbell chart (2017 vs 2019)
# ============================================================
ba_long = before_after.melt(
    id_vars=['Facility Type', 'Drop'],
    value_vars=['Pass_2017', 'Pass_2019'],
    var_name='Year', value_name='Pass Rate'
)
ba_long['Year'] = ba_long['Year'].map({'Pass_2017': '2017', 'Pass_2019': '2019'})

bars = alt.Chart(before_after).mark_bar(height=4, color='#bbb').encode(
    y=alt.Y('Facility Type:N', sort=alt.SortField('Drop', order='descending'), title=None),
    x=alt.X('Pass_2019:Q', title='Pass Rate (%)', scale=alt.Scale(domain=[0, 100])),
    x2='Pass_2017:Q'
)
dots = alt.Chart(ba_long).mark_circle(size=200, opacity=1).encode(
    y=alt.Y('Facility Type:N', sort=alt.SortField('Drop', order='descending'), title=None),
    x=alt.X('Pass Rate:Q'),
    color=alt.Color('Year:N',
                    scale=alt.Scale(domain=['2017', '2019'], range=['#27ae60', '#c0392b']),
                    legend=alt.Legend(title='Year', orient='top')),
    tooltip=['Facility Type:N', 'Year:N', alt.Tooltip('Pass Rate:Q', format='.1f')]
)
labels = alt.Chart(before_after).mark_text(
    align='left', dx=8, fontSize=11, fontWeight='bold', color='#c0392b'
).encode(
    y=alt.Y('Facility Type:N', sort=alt.SortField('Drop', order='descending')),
    x='Pass_2017:Q',
    text=alt.Text('Drop:Q', format='.1f')
)
dumbbell = (bars + dots + labels).properties(
    width='container', height=320,
    title=alt.TitleParams(
        text='Two Years, One Rule Change',
        subtitle='Pass rates collapsed across every facility type between 2017 and 2019. Numbers show percentage-point drop.',
        fontSize=16, anchor='start', color='#2c3e50'
    )
).configure_view(stroke=None).configure_axis(grid=True, gridColor='#EEE')
dumbbell.save(chart_path('before_after.html'))
print("[OK] before_after.html")


# ============================================================
# CHART 3 — Heatmap
# ============================================================
heatmap = alt.Chart(yearly_pass).mark_rect().encode(
    x=alt.X('Year:O', title='Year'),
    y=alt.Y('Facility Type:N', sort=FACILITY_ORDER, title=None),
    color=alt.Color('Pass Rate:Q',
                    scale=alt.Scale(scheme='redyellowgreen', domain=[0, 100]),
                    legend=alt.Legend(title='Pass Rate (%)', orient='right')),
    tooltip=[alt.Tooltip('Facility Type:N'), alt.Tooltip('Year:O'),
             alt.Tooltip('Pass Rate:Q', format='.1f'),
             alt.Tooltip('Total:Q', title='Inspections', format=',')]
).properties(
    width='container', height=320,
    title=alt.TitleParams(
        text='Where the Failures Concentrated',
        subtitle='Red = low pass rate, green = high. The 2018–2019 column lights up red across nearly every row.',
        fontSize=16, anchor='start', color='#2c3e50'
    )
)
heatmap_text = alt.Chart(yearly_pass).mark_text(fontSize=9).encode(
    x='Year:O',
    y=alt.Y('Facility Type:N', sort=FACILITY_ORDER),
    text=alt.Text('Pass Rate:Q', format='.0f'),
    color=alt.condition(
        'datum["Pass Rate"] < 35 || datum["Pass Rate"] > 75',
        alt.value('white'), alt.value('black')
    )
)
heatmap_full = (heatmap + heatmap_text).configure_view(stroke=None).configure_axis(
    labelFontSize=11, titleFontSize=12, labelLimit=200
)
heatmap_full.save(chart_path('heatmap.html'))
print("[OK] heatmap.html")


# ============================================================
# CHART 4 — Pictograph
# ============================================================
group_order = [
    'All Chicago Food Businesses',
    'Retail Food (restaurants, grocery, bakery)',
    'Mobile Food (trucks & carts)',
    'Wholesale Food',
]
result_palette = alt.Scale(
    domain=['Pass', 'Pass w/ Conditions', 'Fail'],
    range=['#27ae60', '#f39c12', '#c0392b']
)
inner = alt.Chart(pictograph_df).mark_point(
    filled=True, size=110, shape='square'
).encode(
    x=alt.X('Col:O', axis=None),
    y=alt.Y('Row:O', axis=None, sort='descending'),
    color=alt.Color('Result:N', scale=result_palette,
                    legend=alt.Legend(title=None, orient='top',
                                      labelFontSize=12, symbolSize=120)),
    tooltip=[alt.Tooltip('Group:N', title='Group'),
             alt.Tooltip('Result:N', title='Outcome'),
             alt.Tooltip('N_total:Q', title='Sample size', format=',')]
).properties(width=240, height=240)

pictograph = inner.facet(
    facet=alt.Facet('Group:N', title=None, sort=group_order,
                    header=alt.Header(labelFontSize=13, labelFontWeight='bold',
                                      labelLimit=300, labelPadding=10)),
    columns=2,
    title=alt.TitleParams(
        text='Of Every 100 New Chicago Food Businesses, How Many Pass on Day One?',
        subtitle=('Each square represents 1% of first-ever inspections in that category. '
                  'Green = clean pass, amber = pass with conditions, red = fail.'),
        fontSize=15, anchor='start', color='#2c3e50',
        subtitleFontSize=11, subtitleColor='#666'
    )
).resolve_scale(x='shared', y='shared').configure_view(stroke=None)
pictograph.save(chart_path('pictograph_first_inspection.html'))
print("[OK] pictograph_first_inspection.html")


# ============================================================
# CHART 5 — Active-uninspected bars
# ============================================================
sort_order = active_uninsp.sort_values(
    'Pct Never Inspected', ascending=False
)['Display Label'].tolist()

uninsp_bars = alt.Chart(active_uninsp).mark_bar(
    color='#c0392b', cornerRadiusTopRight=3, cornerRadiusBottomRight=3
).encode(
    y=alt.Y('Display Label:N', sort=sort_order, title=None,
            axis=alt.Axis(labelLimit=320, labelFontSize=12)),
    x=alt.X('Pct Never Inspected:Q',
            title='% of active mature licenses never inspected',
            scale=alt.Scale(domain=[0, 100])),
    tooltip=[
        alt.Tooltip('Display Label:N',       title='Category'),
        alt.Tooltip('Active Licenses:Q',     title='Active mature licenses', format=','),
        alt.Tooltip('Inspected:Q',           title='Inspected',              format=','),
        alt.Tooltip('Never Inspected:Q',     title='Never inspected',        format=','),
        alt.Tooltip('Pct Never Inspected:Q', title='% never inspected',      format='.1f')
    ]
)
active_uninsp['count_label'] = (
    active_uninsp['Never Inspected'].astype(int).astype(str)
    + ' of '
    + active_uninsp['Active Licenses'].astype(int).map('{:,}'.format)
)
count_labels = alt.Chart(active_uninsp).mark_text(
    align='left', dx=8, fontSize=11, color='#444'
).encode(
    y=alt.Y('Display Label:N', sort=sort_order),
    x=alt.X('Pct Never Inspected:Q'),
    text='count_label:N'
)
uninspected_chart = alt.layer(uninsp_bars, count_labels).properties(
    width='container', height=280,
    title=alt.TitleParams(
        text="Where Chicago's Inspection Gaps Concentrate",
        subtitle='Share of long-active food licenses (2+ years) that have never received a CDPH inspection.',
        fontSize=15, anchor='start', color='#2c3e50',
        subtitleFontSize=11, subtitleColor='#666'
    )
).configure_view(stroke=None).configure_axis(
    grid=True, gridColor='#EEE', labelFontSize=11, titleFontSize=12
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
uninspected_dots = uninspected_dots.dropna(subset=['latitude', 'longitude'])

geo_data = alt.Data(values=chicago_geo['features'])

choropleth = alt.Chart(geo_data).mark_geoshape(stroke='white', strokeWidth=0.5).encode(
    color=alt.Color('pct_uninspected:Q',
                    scale=alt.Scale(scheme='reds', domain=[0, 10], clamp=True),
                    legend=alt.Legend(title='% never inspected', orient='right', format='.0f')),
    tooltip=[
        alt.Tooltip('properties.ZIP:N',  title='ZIP code'),
        alt.Tooltip('total_active:Q',    title='Active Retail Food licenses', format=','),
        alt.Tooltip('uninspected:Q',     title='Never inspected',             format=','),
        alt.Tooltip('pct_uninspected:Q', title='% never inspected',           format='.1f')
    ]
).transform_lookup(
    lookup='properties.ZIP',
    from_=alt.LookupData(zip_coverage, 'zip_code',
                         ['total_active', 'uninspected', 'pct_uninspected'])
).project(type='mercator').properties(width='container', height=720)

dots_layer = alt.Chart(uninspected_dots).mark_circle(
    color='#2c3e50', opacity=0.7, size=18, stroke='white', strokeWidth=0.5
).encode(
    longitude='longitude:Q', latitude='latitude:Q',
    tooltip=[alt.Tooltip('zip_code:N', title='ZIP'),
             alt.Tooltip('license_number:Q', title='License #')]
)
map_chart = alt.layer(choropleth, dots_layer).properties(
    title=alt.TitleParams(
        text="Where Chicago's Uninspected Restaurants Live",
        subtitle=("Each dot is a long-active retail food business that has never been inspected. "
                  "ZIP fill = share of that ZIP's licensed retail food businesses never inspected."),
        fontSize=15, anchor='start', color='#2c3e50',
        subtitleFontSize=11, subtitleColor='#666'
    )
).configure_view(stroke=None)
map_chart.save(chart_path('chicago_inspection_map.html'))
print("[OK] chicago_inspection_map.html")

print(f"\nDone — 6 HTML files written to: {CHARTS_DIR}")
