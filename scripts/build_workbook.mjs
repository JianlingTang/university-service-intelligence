import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.env.USI_PROJECT_ROOT
  ? path.resolve(process.env.USI_PROJECT_ROOT)
  : path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const outputDir = path.join(root, "outputs", "university_service_intelligence");
const previewDir = path.join(root, "tmp", "workbook_previews");
await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const workbook = Workbook.create();
const navy = "#102A43";
const blue = "#156B8A";
const teal = "#2A9D8F";
const amber = "#E9A23B";
const red = "#C84630";
const light = "#F5F7FA";
const line = "#D9E2EC";
const white = "#FFFFFF";
const muted = "#627D98";

function titleBand(sheet, range, title, subtitle) {
  sheet.getRange(range).format.fill = navy;
  sheet.getRange(range).format.font = { color: white };
  sheet.getRange("A1:H1").merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format.font = { bold: true, color: white, size: 18 };
  sheet.getRange("A2:H2").merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A2").format.font = { color: "#D9EAF2", size: 10 };
  sheet.getRange("A1:H2").format.rowHeight = 24;
}

function styleHeader(range) {
  range.format.fill = blue;
  range.format.font = { bold: true, color: white };
  range.format.wrapText = true;
  range.format.rowHeight = 30;
}

function styleTable(sheet, usedRange) {
  sheet.showGridLines = false;
  const range = sheet.getRange(usedRange);
  range.format.font = { color: navy, size: 9 };
  range.format.wrapText = true;
  range.format.borders = { insideHorizontal: { style: "thin", color: line } };
  range.format.autofitColumns();
  range.format.autofitRows();
  sheet.freezePanes.freezeRows(1);
}

async function addCsvSheet(sheetName, csvPath) {
  const text = await fs.readFile(csvPath, "utf8");
  const rows = parseCsv(text).map((row, rowIndex) => row.map((value) => {
    if (rowIndex === 0 || value === "") return value;
    if (/^-?\d+(?:\.\d+)?$/.test(value)) return Number(value);
    return value;
  }));
  const sheet = workbook.worksheets.add(sheetName);
  sheet.getRangeByIndexes(0, 0, rows.length, rows[0].length).values = rows;
  const used = sheet.getUsedRange();
  sheet.showGridLines = false;
  used.format.font = { color: navy, size: 9 };
  used.format.wrapText = true;
  used.format.borders = { insideHorizontal: { style: "thin", color: line } };
  used.format.autofitColumns();
  used.format.autofitRows();
  sheet.freezePanes.freezeRows(1);
  styleHeader(used.getRow(0));
  return sheet;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows;
}

const readme = workbook.worksheets.add("Read Me");
readme.showGridLines = false;
titleBand(readme, "A1:H2", "University Service Intelligence & Action Hub", "Synthetic Power BI implementation pack aligned to the Analytics Specialist position description");
readme.getRange("A4:B12").values = [
  ["Artifact", "Purpose"],
  ["Curated CSV model", "Import-ready fact and dimension tables for Power BI Desktop"],
  ["SQLite database", "Reproducible SQL transformation and local analytics application source"],
  ["DAX measure library", "Operational efficiency, experience, forecast and data-health measures"],
  ["Four dashboard mockups", "Executive, bottleneck, experience and action page specifications"],
  ["Forecast model", "Seasonal regression, 12-week outlook and holdout evaluation"],
  ["Action Console", "Read-only local application for evidence, forecast and scenario analysis"],
  ["JD alignment", "Traceability to Position Summary, Responsibilities, Skills and Work Experience"],
  ["Important", "All figures are synthetic and do not represent University of Sydney performance"],
];
styleHeader(readme.getRange("A4:B4"));
readme.getRange("A5:A12").format.font = { bold: true, color: navy };
readme.getRange("A4:B12").format.borders = { insideHorizontal: { style: "thin", color: line } };
readme.getRange("A4:B12").format.wrapText = true;
readme.getRange("A4:B12").format.autofitRows();
readme.getRange("A:B").format.columnWidth = 28;
readme.getRange("B:B").format.columnWidth = 76;
readme.getRange("A14:H15").merge();
readme.getRange("A14").values = [["Build the PBIX in Windows Power BI Desktop using powerbi/BUILD_GUIDE.md. The repository deliberately does not include a fabricated PBIX binary generated outside Power BI Desktop."]];
readme.getRange("A14:H15").format = { fill: "#FFF3D6", font: { color: "#7C4D00", bold: true }, wrapText: true };

const validation = await addCsvSheet("Validation", path.join(root, "data", "curated", "validation_summary.csv"));
validation.getRange("B2:B20").format.numberFormat = "#,##0";

const scenarioValidation = await addCsvSheet("Scenario QA", path.join(root, "data", "curated", "seeded_scenario_validation.csv"));
scenarioValidation.getRange("B2:C20").format.numberFormat = "0.0%";

const forecastQa = await addCsvSheet("Forecast QA", path.join(root, "data", "curated", "forecast_model_evaluation.csv"));
forecastQa.getRange("E2:F20").format.numberFormat = "0.00";
forecastQa.getRange("G2:H20").format.numberFormat = "0.0%";

const actions = await addCsvSheet("Action Register", path.join(root, "data", "curated", "fact_action_insight.csv"));
actions.getRange("G2:G20").format.numberFormat = "0.0%";
actions.getRange("I2:I20").format.numberFormat = "0.0%";
actions.getRange("T2:T20").format.numberFormat = "0.0%";
actions.getRange("U2:U20").format.numberFormat = "0.0%";
actions.getRange("V2:V20").format.numberFormat = "0.0%";
actions.getRange("O2:Q20").format.numberFormat = "0.0%";
actions.freezePanes.freezeRows(1);

const jd = workbook.worksheets.add("JD Alignment");
jd.showGridLines = false;
jd.getRange("A1:C18").values = [
  ["Position requirement", "Project evidence", "Status"],
  ["Multi-source actionable insights", "Cases, events, contacts, feedback, workforce, contractors, digital journey and population", "Implemented"],
  ["Staff and student experience", "CSAT, CES, repeat demand, requester and lifecycle segmentation", "Implemented"],
  ["Stakeholder partnership", "Decision-owner brief, acceptance criteria and action ownership", "Demonstrated method"],
  ["SQL and Python", "Deterministic generator, SQLite transformations and validation", "Implemented"],
  ["Power BI and multidimensional modelling", "Star schema, DAX, theme and four page specifications", "PBIX assembly required"],
  ["Forecast future trends", "Seasonal regression, 12-week forecast, 95% interval and holdout WAPE", "Implemented"],
  ["Trusted-advisor recommendations", "Eight recommendations with evidence, owner, baseline, target and review", "Implemented"],
  ["Student lifecycle", "Pre-enrolment, Commencing, Continuing and Completing dimension", "Implemented"],
  ["Root cause and impact assessment", "Stage time, handoffs, repeat contact, rework and benefit tracking", "Implemented"],
  ["Data quality/data health", "Injected defects, SQL remediation, issue register and visible QA", "Implemented"],
  ["Demand pipeline", "Weekly workload/capacity and forward scenario analysis", "Implemented"],
  ["AI/ML", "AI-ready contract and statistical forecast; no LLM claimed in v1", "Partial/future companion"],
  ["Snowflake and Azure", "Target production architecture and Snowflake DDL", "Designed, not deployed"],
  ["Analytics application development", "Read-only API and local Action Console", "Implemented"],
  ["Executive communication", "Direct KPI hierarchy, evidence statements and action register", "Implemented"],
  ["Agile/iterative delivery", "MVP boundaries, prioritised backlog and separated future AI increment", "Implemented"],
  ["Attention to detail", "Automated reconciliation, scenario tests and explicit metric exclusions", "Implemented"],
];
styleTable(jd, "A1:C18");
styleHeader(jd.getRange("A1:C1"));
jd.getRange("A:A").format.columnWidth = 34;
jd.getRange("B:B").format.columnWidth = 76;
jd.getRange("C:C").format.columnWidth = 24;
jd.getRange("C2:C18").conditionalFormats.add("containsText", { text: "Implemented", format: { fill: "#DDF3EE", font: { color: "#146B5A", bold: true } } });
jd.getRange("C2:C18").conditionalFormats.add("containsText", { text: "Partial", format: { fill: "#FFF3D6", font: { color: "#7C4D00", bold: true } } });

const kpi = workbook.worksheets.add("KPI Definitions");
kpi.showGridLines = false;
kpi.getRange("A1:C19").values = [
  ["Metric", "Definition", "Decision supported"],
  ["Cases received", "Distinct valid submitted cases", "Demand volume"],
  ["Cases closed", "Distinct cases resolved", "Throughput"],
  ["Open backlog as of", "Submitted by selected date and unresolved at that date", "Operational workload"],
  ["Cases per 1,000", "Cases divided by average monthly active population x 1,000", "Fair cohort comparison"],
  ["Median/P90 resolution", "Typical and tail business resolution time", "Experience and risk"],
  ["SLA compliance", "1 minus eligible resolution breaches divided by eligible resolved cases", "Service performance"],
  ["First-contact resolution", "Resolved without repeat, handoff or reopen", "Quality"],
  ["Repeat contact 14d", "Requester-initiated additional contact within 14 days", "Failure demand"],
  ["Handoff rate", "Cases transferred at least once divided by cases", "Ownership clarity"],
  ["Reopen rate", "Reopened divided by eligible resolved", "Outcome quality"],
  ["Cost per resolved case", "Estimated operational cost divided by eligible resolved", "Efficiency"],
  ["Capacity gap", "Required handle hours minus staffed productive hours", "Workforce planning"],
  ["Self-service completion", "Successful completions divided by sessions", "Digital friction"],
  ["Contractor rework", "Work orders requiring repeat work divided by work orders", "Vendor quality"],
  ["CSAT positive", "Post-case scores 4 or 5 divided by valid responses", "Satisfaction"],
  ["Customer effort", "Average CES from 1 difficult to 5 easy", "Friction"],
  ["Forecast WAPE", "Absolute holdout error divided by actual holdout demand", "Model assurance"],
  ["Avoidable staff hours", "Transparent estimate attached to each action", "Prioritisation"],
];
styleTable(kpi, "A1:C19");
styleHeader(kpi.getRange("A1:C1"));
kpi.getRange("A:A").format.columnWidth = 30;
kpi.getRange("B:B").format.columnWidth = 74;
kpi.getRange("C:C").format.columnWidth = 30;

const dictionary = workbook.worksheets.add("Data Model");
dictionary.showGridLines = false;
dictionary.getRange("A1:C20").values = [
  ["Table", "Grain", "Purpose"],
  ["FactCase", "One curated service case", "Demand, SLA, cost, ownership and lifecycle"],
  ["FactCaseEvent", "One workflow event", "Historical flow and bottleneck analysis"],
  ["FactInteraction", "One contact", "Repeat contact and channel analysis"],
  ["FactFeedback", "One response", "Student, staff and contractor experience"],
  ["FactCapacityWeekly", "One team-week", "Demand, workload and capacity"],
  ["FactWorkOrder", "One work order", "Facilities contractor performance"],
  ["FactDigitalJourneyDaily", "One service-day", "Self-service and deflection"],
  ["FactPopulationMonthly", "One month-campus-cohort-stage", "Population denominator"],
  ["FactActionInsight", "One recommendation", "Evidence, owner, target and outcome"],
  ["FactDemandForecast", "One service-week-model", "Historical fit and 12-week forecast"],
  ["ForecastModelEvaluation", "One service-model", "Holdout MAE, RMSE, WAPE and bias"],
  ["DimDate", "One day", "Calendar and academic phase"],
  ["DimService", "One service", "Enterprise service scope"],
  ["DimTeam", "One owner team", "Operational accountability"],
  ["DimCampus", "One campus", "Location segmentation"],
  ["DimCohort", "One requester cohort", "Equity and requester analysis"],
  ["DimLifecycleStage", "One journey stage", "Student lifecycle context"],
  ["DimChannel", "One channel", "Contact mode"],
  ["DimSLA", "One priority", "Response and resolution target"],
];
styleTable(dictionary, "A1:C20");
styleHeader(dictionary.getRange("A1:C1"));
dictionary.getRange("A:A").format.columnWidth = 32;
dictionary.getRange("B:B").format.columnWidth = 36;
dictionary.getRange("C:C").format.columnWidth = 60;

const overview = workbook.worksheets.add("QA Overview");
overview.showGridLines = false;
titleBand(overview, "A1:H2", "Implementation QA Overview", "Formula-linked counts, forecast quality and action opportunity snapshot");
overview.getRange("A4:F4").values = [["Curated cases", "Events", "Interactions", "Feedback", "Actions", "Forecast WAPE"]];
overview.getRange("A5:F5").formulas = [["='Validation'!B2", "='Validation'!B3", "='Validation'!B4", "='Validation'!B5", "='Validation'!B7", "=AVERAGE('Forecast QA'!G2:G4)"]];
overview.getRange("A4:F4").format = { fill: light, font: { color: muted, bold: true }, wrapText: true };
overview.getRange("A5:E5").format = { font: { color: navy, bold: true, size: 18 }, numberFormat: "#,##0" };
overview.getRange("F5").format = { font: { color: navy, bold: true, size: 18 }, numberFormat: "0.0%" };
overview.getRange("A4:F5").format.borders = { preset: "outside", style: "thin", color: line };
overview.getRange("A4:F5").format.columnWidth = 20;

overview.getRange("A8:B8").values = [["Action", "Avoidable hours"]];
for (let i = 0; i < 8; i += 1) {
  overview.getRange(`A${9+i}:B${9+i}`).formulas = [[`='Action Register'!A${2+i}`, `='Action Register'!V${2+i}`]];
}
styleHeader(overview.getRange("A8:B8"));
overview.getRange("B9:B16").format.numberFormat = "#,##0.0";
const actionChart = overview.charts.add("bar", overview.getRange("A8:B16"));
actionChart.title = "Estimated avoidable staff hours by action";
actionChart.hasLegend = false;
actionChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
actionChart.yAxis = { numberFormatCode: "#,##0" };
actionChart.setPosition("D8", "K24");

for (const sheetName of ["Read Me", "Validation", "Scenario QA", "Forecast QA", "Action Register", "JD Alignment", "KPI Definitions", "Data Model", "QA Overview"]) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "-").toLowerCase()}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const inspection = await workbook.inspect({ kind: "table", range: "QA Overview!A1:F16", include: "values,formulas", tableMaxRows: 16, tableMaxCols: 6, maxChars: 6000 });
console.log(inspection.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan" });
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir, "university_service_intelligence_implementation_pack.xlsx"));
