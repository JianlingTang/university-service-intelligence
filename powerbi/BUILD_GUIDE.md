# Power BI 网页端搭建指南

整个流程都在浏览器里完成：在 [app.powerbi.com](https://app.powerbi.com) 建语义模型和报表，然后用 Publish to web 公开发布。不需要 Windows，也不需要 Power BI Desktop。界面按钮和菜单名保留英文，和 Power BI 界面一致。

用到的文件：

- `powerbi/power_query.pq`：每张表一个 Power Query 查询，列类型都已写明，数据从 GitHub 上的 `data/curated` 读取。
- `powerbi/measures.dax`：一个 DAX 查询，包含全部 measure，运行后返回一行对账结果。
- `powerbi/theme.json`：报表主题。
- `mockups/*.png`：每一页的目标布局。

模型有意不导入 `fact_case_event` 和 `fact_interaction`：四个页面都用不到它们，导入后还会形成 fact 表之间的筛选路径，让筛选结果产生歧义。

## 0. 准备工作

1. **账号。** Power BI 只接受工作或学校账号。Publish to web 还要求租户设置 *Publish to web* 处于开启状态（见第 7 步）。大学租户的管理员通常会关掉这个设置，遇到这种情况，要换一个你自己是管理员的租户（例如开通 Microsoft 365 Business 试用时创建的租户），再用那个账号登录 Power BI。
2. **所有操作都在 *My workspace* 里做。** 从 My workspace 发布到 web 只需要免费的 Power BI 许可证，其他 workspace 需要 Pro。
3. **CSV 是公开的。** 数据放在公开 repo 里（都是合成数据）。先确认下面这个链接能下载到文件：
   `https://raw.githubusercontent.com/JianlingTang/university-service-intelligence/main/data/curated/dim_campus.csv`

## 1. 创建查询

1. 在 Power BI 左侧点 **Create** → **Get data** → **Blank query**。
2. 按 `power_query.pq` 里的顺序逐个创建查询。每个查询的做法都一样：**New query → Blank query**，把查询名改成注释里 `Query name` 后面的名字，打开 **Advanced editor**，粘贴正文。
   - 先建 `BaseUrl`。它已经指向这个 repo，除非你 fork 了 repo，否则不用改。
   - 再建 `LoadCsv`。它是一个函数，不会加载成表。
   - 最后建 18 个表查询（从 `DimDate` 到 `DataQualityIssues`）。
3. 第一次运行查询时会要求设置连接：认证方式选 **Anonymous**，隐私级别选 **Public**。
4. 检查每一列的列标题，确认没有错误图标。列类型已经写死在脚本里，不要让 Power Query 自动改类型。
5. 选择 **Create a semantic model only**，命名为 `University Service Intelligence`。

## 2. 模型设置（打开语义模型 → 切换到 Editing mode）

1. **计算表**（Home → New table）：

   ```dax
   _Measures = { BLANK () }
   ```

   ```dax
   AgeingBand =
   DATATABLE (
       "band", STRING, "sort_order", INTEGER, "min_days", INTEGER, "max_days", INTEGER,
       { { "0–7 days", 1, 0, 7 }, { "8–14 days", 2, 8, 14 }, { "15–30 days", 3, 15, 30 }, { "30+ days", 4, 31, 100000 } }
   )
   ```

   隐藏 `_Measures[Value]` 列。`AgeingBand` 不和任何表建关系。

2. **计算列**（在 `FactFeedback` 上点 New column）。这两列把每条问卷对应到它所属 case 的解决时长分段，不需要建 fact 表之间的关系：

   ```dax
   resolution_time_band =
   LOOKUPVALUE ( FactCase[resolution_time_band], FactCase[case_id], FactFeedback[related_case_id] )
   ```

   ```dax
   resolution_band_order =
   SWITCH ( FactFeedback[resolution_time_band], "0–8h", 1, "9–24h", 2, "25–80h", 3, "80h+", 4, "Open/Excluded", 5 )
   ```

3. **日期表。** 右键 `DimDate` → **Mark as date table**，日期列选 `date`。
4. **Sort by column**（在 Properties 面板里设置）：
   - `DimDate[month_name]` 按 `month_number` 排序
   - `DimLifecycleStage[lifecycle_stage]` 按 `lifecycle_stage_key` 排序
   - `AgeingBand[band]` 按 `sort_order` 排序
   - `FactFeedback[resolution_time_band]` 按 `resolution_band_order` 排序

## 3. 关系

打开 **Manage relationships**，先**删掉所有自动检测出来的关系**，尤其是 fact 表之间的关系，例如 `FactCase[case_id]` ↔ `FactWorkOrder[case_id]`。然后按下表建关系：全部是多对一（维度表在"一"的一侧），交叉筛选方向都选 **Single**。

| 从（多） | 到（一） | 是否激活 |
|---|---|---|
| `FactCase[submitted_date_key]` | `DimDate[date_key]` | 是 |
| `FactCase[closed_date_key]` | `DimDate[date_key]` | **否**（供 `Cases Closed` 使用） |
| `FactFeedback[feedback_date_key]` | `DimDate[date_key]` | 是 |
| `FactCapacityWeekly[week_date_key]` | `DimDate[date_key]` | 是 |
| `FactDemandForecast[week_date_key]` | `DimDate[date_key]` | 是 |
| `FactDigitalJourneyDaily[date_key]` | `DimDate[date_key]` | 是 |
| `FactPopulationMonthly[month_date_key]` | `DimDate[date_key]` | 是 |
| `FactCase`、`FactFeedback`、`FactCapacityWeekly`、`FactDemandForecast`、`FactDigitalJourneyDaily`、`FactActionInsight`、`ForecastModelEvaluation` 的 `[service_key]` | `DimService[service_key]` | 是 |
| `FactCase`、`FactCapacityWeekly`、`FactWorkOrder` 的 `[team_key]` | `DimTeam[team_key]` | 是 |
| `FactActionInsight[suggested_owner_team_key]` | `DimTeam[team_key]` | 是 |
| `FactCase`、`FactFeedback`、`FactWorkOrder`、`FactPopulationMonthly` 的 `[campus_key]` | `DimCampus[campus_key]` | 是 |
| `FactCase`、`FactFeedback`、`FactPopulationMonthly` 的 `[cohort_key]` | `DimCohort[cohort_key]` | 是 |
| `FactCase`、`FactPopulationMonthly` 的 `[lifecycle_stage_key]` | `DimLifecycleStage[lifecycle_stage_key]` | 是 |
| `FactCase[channel_key]` | `DimChannel[channel_key]` | 是 |
| `FactCase[priority]` | `DimSLA[priority]` | 是 |

不要在 `DimTeam` 和 `DimService` 之间建关系。`DimTeam[service_key]` 只是一个描述性字段。

隐藏所有 `*_key` 列和所有 `synthetic_label` 列。

## 4. Measure

1. 在语义模型上选择 **Write DAX queries**。如果这个选项是灰色的，到 workspace 设置里打开 *Users can edit data models in the Power BI service*。
2. 粘贴 `measures.dax` 的全部内容，点 **Run**。结果只有一行，逐项和第 5 节对照。
3. 点 **Update model with changes**。45 个 measure 会连同说明一起保存到 `_Measures` 表。
4. 在 Properties 面板里设置格式字符串（按住 Ctrl 可以一次选中多个 measure）：
   - 计数：`#,##0`
   - 比率和 WAPE：`0.0%`
   - 小时：`0.0`
   - 澳元：`$#,##0`

## 5. 对账

第 4 步的 **Run** 必须返回下表的值。这些期望值是用同样的逻辑，直接从 `data/curated` 独立算出来的。

| Measure | 期望值 |
|---|---|
| Cases Received | 18,000 |
| Cases Closed | 16,566 |
| Open Backlog As Of | 182（与 `validation_summary.csv` 一致） |
| Aged Backlog 7D As Of | 44 |
| SLA Compliance % | 64.0% |
| Median Resolution Business Hours | 29.15 |
| CSAT Positive % | 53.4%（n = 5,400） |
| Forecast Cases Next 12W | 2,070 |
| Forecast Capacity Gap Hours | −157.4（负数表示产能有富余） |
| Forecast WAPE | 13.3% |
| Data Quality Issues | 255 |

另外，以最后一个实际数据日期计算，积压账龄各分段应为：0–7 天 = 138，8–14 天 = 44，更长的分段都是 0。

## 6. 报表

在语义模型里点 **New report**，然后先做全局设置：

- **主题：** View → Themes → Browse for themes → 选择 `theme.json`。
- **画布：** 每一页都用 16:9。
- **顶部筛选栏：** 每页放两个切片器，`DimService[service_name]` 和 `DimCampus[campus_name]`，用 View → Sync slicers 让它们跨页同步。
- **合成数据标识：** 每页加一个文本框，写 *Synthetic demonstration data — not actual University of Sydney results.*
- **未来日期筛选：** DimDate 比实际数据多出 12 周，是为了让预测数据有日期可以关联。所以凡是带日期轴的 visual，**除了预测图**，都要加 visual 级筛选 `DimDate[is_future] = 0`。

布局参考 `mockups/`。下面每一条就是一个 visual。

### 第 1 页 · Executive Operational Health

- **KPI 卡片：** `Cases Received`、`Open Backlog As Of`、`SLA Compliance %`、`Median Resolution Business Hours`、`Display CSAT %`、`Forecast Capacity Gap Hours`。
- **折线图：** 轴用 `DimDate[month_start]`；值用 `Cases Received`、`Cases Closed`。
- **散点（气泡）图**，数据来自 `FactActionInsight`：
  - Values：`issue`
  - X 轴：Sum `estimated_avoidable_staff_hours`
  - Y 轴：Average `negative_experience_rate`
  - Size：Sum `users_affected`
  - Legend：`priority`
- **表格：** `issue`、`evidence_1_name`、`evidence_1_value`、`DimTeam[team_name]`、`recommended_action`、`next_review_date`。

### 第 2 页 · Bottlenecks & Capacity

- **簇状条形图：** `Median Triage Business Hours`、`Median Assignment Business Hours`、`Median Resolution Business Hours`，轴用 `DimService[service_name]`。
- **柱状图：** 轴用 `AgeingBand[band]`；值用 `Open Backlog by Age Band`。
- **预测折线图：**
  - 轴：`FactDemandForecast[week_start]`
  - 值：Sum `actual_cases`、Sum `predicted_cases`
  - 给 predicted 加误差线：下限 `lower_95_cases`，上限 `upper_95_cases`
  - 这个 visual **不加** `is_future` 筛选。
- **折线和簇状柱形图：**
  - 轴：`FactCapacityWeekly[week_start]`
  - 柱：Sum `required_handle_hours`、Sum `staffed_hours`
  - 线：`Capacity Gap Hours`
- **矩阵（Facilities 下钻）：** 行用 `DimCampus[campus_name]` → `FactWorkOrder[category]`；值用 `Contractor On Time %`、`Contractor Rework %`。

### 第 3 页 · Experience & Equity

- **折线和簇状柱形图：** 轴用 `DimDate[month_start]`；柱用 `Valid Post Case Responses`；线用 `Display CSAT %`、`Average Customer Effort`。
- **矩阵：** 行用 `DimCohort[cohort_name]`；列用 `DimLifecycleStage[lifecycle_stage]`；值用 `Display Cases per 1,000`。
- **柱状图：** 轴用 `FactFeedback[resolution_time_band]`；值用 `CSAT Positive %`。筛掉空值和 `Open/Excluded`。
- **条形图：** 轴用 `FactFeedback[feedback_theme]`；Legend 用 `respondent_type`；值用 `feedback_id` 的 Count，按降序排列。
- **折线图：** 轴用 `DimDate[month_start]`；值用 `Self Service Completion %`、`Repeat Contact 14D %`。

### 第 4 页 · Actions & Benefits

- **表格（行动登记表）：** `action_id`、`issue`、`DimTeam[team_name]`、`action_status`、`priority`、`next_review_date`。`priority` 和 `action_status` 用条件格式的**图标**来表示，不要只靠颜色区分。
- **表格：** `action_id`、`success_measure`、`baseline_value`、`target_value`、`actual_value`、`unit`，三个值列加数据条。各项行动的单位不同，如果画在同一个坐标轴上会误导读者。
- **簇状条形图：** 轴用 `issue`；值用 Sum `estimated_avoidable_staff_hours`、Sum `users_affected`。
- **数据健康卡片：** `Data Quality Issues`、`Cases with Repaired Data %`、`Forecast WAPE`。

### 无障碍与 QA

- 给每个 visual 加 alt text（Format → General → Alt text）。
- 给指标加上定义说明的 tooltip。measure 里用 `///` 写的说明会显示在 Data 面板中。
- CSAT 旁边同时显示 `Valid Post Case Responses`。`CSAT Wilson 95%` 置信区间只在 n ≥ 30 时使用；n 不够时这两个 measure 本身就返回空值。
- 每一页都选中一个 service 切片器点一遍，确认卡片数值会跟着变化。

## 7. 发布到 web

1. **开启租户设置**（只有租户管理员能操作）：右上角齿轮 → **Admin portal** → **Tenant settings** → *Export and sharing settings* → **Publish to web** → Enabled → Apply。设置可能要几分钟才生效。
2. **关闭刷新：** 在语义模型设置里把计划刷新（scheduled refresh）**关掉**，数据是静态的。
3. **生成嵌入代码：** 打开报表 → **File → Embed report → Publish to web (public)** → Create embed code → Publish。默认页面选 **第 1 页**，再加一张占位图（第 1 页的截图）。访问量过大时，访客会先看到这张占位图。
4. **分享：**
   - 复制**链接**，放到简历和 LinkedIn 上。
   - 复制 **iframe** 代码，嵌入作品集网站。16:9 的页面用 `960 × 596` 可以避免出现上下黑边。
5. **测试：** 用无痕窗口打开链接，确认不登录也能正常浏览四个页面，切片器也能用。

注意：拿到链接的任何人都能看到模型里的全部数据，不只是 visual 上显示的内容。这里可以接受，只是因为数据全部是合成的。以后要管理或删除这个链接，到 Settings → **Manage embed codes** 里操作。
