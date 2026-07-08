const state = { data: null, game: null, page: 1, pageSize: 10, topic: null };

const languageNames = { english: "英语", schinese: "简体中文", tchinese: "繁体中文", japanese: "日语", koreana: "韩语", russian: "俄语", german: "德语", french: "法语", spanish: "西班牙语", latam: "拉美西语", brazilian: "巴西葡语", portuguese: "葡萄牙语", polish: "波兰语", turkish: "土耳其语", thai: "泰语", italian: "意大利语", ukrainian: "乌克兰语" };
const topics = [
  { id: "performance", name: "性能与优化", description: "帧率、卡顿、显存、CPU/GPU 占用与硬件适配问题。", words: ["performance","fps","frame rate","stutter","lag","optimization","optimiz","crash","性能","优化","帧","卡顿","闪退","崩溃","显存","cpu","gpu","フレーム","最適化","クラッシュ","성능","프레임"] },
  { id: "bugs", name: "Bug 与稳定性", description: "影响正常游玩的错误、存档、连接失败和功能异常。", words: ["bug","broken","error","freeze","glitch","issue","disconnect","server","matchmaking","错误","故障","存档","断线","服务器","联机","バグ","不具合","サーバー","버그","서버"] },
  { id: "content", name: "内容与重复度", description: "内容量、后期体验、任务重复与更新内容是否充足。", words: ["content","endgame","repetitive","boring","mission","quest","update","内容","重复","无聊","任务","后期","更新","コンテンツ","飽き","クエスト","콘텐츠","반복"] },
  { id: "balance", name: "玩法与平衡", description: "战斗、难度、数值、武器与核心循环体验。", words: ["balance","difficulty","combat","weapon","enemy","gameplay","nerf","buff","平衡","难度","战斗","武器","数值","削弱","加强","バランス","武器","戦闘","밸런스","전투"] },
  { id: "price", name: "价格与商业化", description: "售价、DLC、微交易、性价比和商业策略争议。", words: ["price","expensive","dlc","microtransaction","money","refund","worth","价格","售价","退款","氪金","微交易","性价比","値段","課金","환불","가격"] },
  { id: "ux", name: "界面与易用性", description: "操作、菜单、引导、控制器和整体使用体验。", words: ["ui","ux","menu","control","tutorial","interface","keyboard","controller","操作","界面","菜单","引导","手柄","键鼠","操作性","メニュー","操作","조작","인터페이스"] },
  { id: "community", name: "账号与社区事件", description: "账号绑定、地区限制、反作弊和开发商沟通。", words: ["account","psn","region","sony","developer","community","anti-cheat","ban","账号","绑定","地区","索尼","运营","社区","封禁","アカウント","地域","계정","지역"] },
];

const $ = (selector) => document.querySelector(selector);
const pct = (value) => `${Math.round(value * 100)}%`;
const hours = (minutes) => `${(minutes / 60).toFixed(minutes >= 600 ? 0 : 1)}h`;
const escapeHtml = (text) => String(text).replace(/[&<>"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[char]));
const dateText = (timestamp) => new Date(timestamp * 1000).toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });

function classify(review) {
  const text = review.review.toLowerCase();
  return topics.filter((topic) => topic.words.some((word) => text.includes(word.toLowerCase()))).map((topic) => topic.id);
}

function enrichGame(game) {
  game.reviews.forEach((review) => { if (!Array.isArray(review.topics)) review.topics = classify(review); });
  return game;
}

function positiveRate(items) { return items.length ? items.filter((item) => item.voted_up).length / items.length : 0; }
function median(values) { const sorted = [...values].sort((a,b) => a-b); return sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0; }
function quantile(values, q) { const sorted=[...values].sort((a,b)=>a-b); if(!sorted.length)return 0; return sorted[Math.floor((sorted.length-1)*q)]; }
function wilson(items) {
  const n=items.length; if(!n)return {low:0,high:0,margin:0}; const p=positiveRate(items), z=1.96, z2=z*z;
  const center=(p+z2/(2*n))/(1+z2/n); const spread=z*Math.sqrt((p*(1-p)+z2/(4*n))/n)/(1+z2/n);
  return {low:Math.max(0,center-spread),high:Math.min(1,center+spread),margin:spread};
}
function confidenceText(items) { const ci=wilson(items); return items.length<30?`样本较少（n=${items.length}）`:`95% CI ${pct(ci.low)}—${pct(ci.high)}`; }

function renderGameIndex() {
  $("#game-index").innerHTML = state.data.games.map((game, index) => `
    <button class="game-tab ${game === state.game ? "active" : ""}" style="--game-accent:${game.accent}" data-game="${index}">
      <small>0${index + 1} / ${game.app_id}</small><b>${escapeHtml(game.name_zh)}</b><span>${escapeHtml(game.name)}</span>
    </button>`).join("");
  document.querySelectorAll(".game-tab").forEach((button) => button.addEventListener("click", () => selectGame(Number(button.dataset.game))));
}

function renderFocus() {
  const game = state.game, reviews = game.reviews, rate = positiveRate(reviews);
  document.documentElement.style.setProperty("--accent", game.accent);
  $("#game-image").src = game.image; $("#game-image").alt = `${game.name_zh} Steam 头图`;
  $("#game-appid").textContent = `APP ${game.app_id} · RELEASED ${game.released}`;
  $("#game-name").textContent = game.name_zh; $("#game-focus").textContent = game.focus;
  const label = rate >= .85 ? "口碑强劲" : rate >= .7 ? "整体偏正向" : rate >= .5 ? "评价分化" : "负面压力突出";
  $("#verdict").innerHTML = `<small>近期样本判断</small><strong>${label}</strong><span>${reviews.length} 条近期评论中，${pct(rate)} 表示推荐。</span>`;
  const dates = reviews.map((r) => r.created);
  $("#sample-range").textContent = `${dateText(Math.min(...dates))} — ${dateText(Math.max(...dates))}`;
  $("#sample-count").textContent = `${reviews.length} 条 / 多语言`;
}

function renderMetrics() {
  const reviews = state.game.reviews;
  const languageCount = new Set(reviews.map((r) => r.language)).size;
  const medianPlaytime = median(reviews.map((r) => r.playtime_at_review));
  const useful = [...reviews].sort((a,b) => b.votes_up - a.votes_up)[0];
  $("#metrics").innerHTML = [
    ["近期推荐率", pct(positiveRate(reviews)), confidenceText(reviews)],
    ["负面样本", reviews.filter(r => !r.voted_up).length, "用于定位主要问题"],
    ["覆盖语言", languageCount, "保留原始语言文本"],
    ["评论时长中位数", hours(medianPlaytime), `最高赞评论 ${useful?.votes_up || 0} 赞`],
  ].map(([label,value,note]) => `<article class="metric"><small>${label}</small><strong>${value}</strong><span>${note}</span></article>`).join("");
}

function renderComparison() {
  const rows=state.data.games.map(game=>{const stats=topicStats(game), top=stats[0]; return {game,rate:positiveRate(game.reviews),negative:game.reviews.filter(r=>!r.voted_up).length,top:top?.name||"未识别",median:median(game.reviews.map(r=>r.playtime_at_review))};});
  $("#comparison-table").innerHTML=rows.map(item=>`<button class="comparison-row ${item.game===state.game?"active":""}" data-compare-game="${state.data.games.indexOf(item.game)}" style="--row-accent:${item.game.accent}"><span><i></i><b>${item.game.name_zh}</b></span><span><small>推荐率</small><strong>${pct(item.rate)}</strong></span><span><small>负面样本</small><strong>${item.negative}</strong></span><span><small>首要问题</small><strong>${item.top}</strong></span><span><small>时长中位数</small><strong>${hours(item.median)}</strong></span></button>`).join("");
  document.querySelectorAll("[data-compare-game]").forEach(button=>button.addEventListener("click",()=>selectGame(Number(button.dataset.compareGame))));
}

function trendBuckets(reviews) {
  const groups = new Map();
  reviews.forEach((review) => {
    const date = new Date(review.created * 1000);
    const key = date.toISOString().slice(0,10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(review);
  });
  if (groups.size >= 3) return [...groups.entries()].sort(([a],[b]) => a.localeCompare(b)).slice(-30).map(([key,items]) => ({ label: key.slice(5), rate: positiveRate(items), count: items.length }));
  const sorted = [...reviews].sort((a,b) => a.created - b.created);
  const size = Math.ceil(sorted.length / 10);
  return Array.from({length: 10}, (_,i) => { const items = sorted.slice(i*size,(i+1)*size); return {label:`批次 ${i+1}`,rate:positiveRate(items),count:items.length}; }).filter(x => x.count);
}

function renderTrend() {
  const history=(state.data.snapshots||[]).map(snapshot=>({snapshot,data:snapshot.games?.[String(state.game.app_id)]})).filter(item=>item.data);
  const hasHistory=history.length>=7;
  const recentHistory=history.slice(-30);
  const buckets = hasHistory ? recentHistory.map(item=>({label:item.snapshot.date.slice(5),rate:item.data.positive_rate,count:item.data.sample_count})) : trendBuckets(state.game.reviews);
  const usesBatches=!hasHistory && buckets[0]?.label.startsWith("批次");
  $("#trend-title").textContent=hasHistory?"近 30 日口碑快照":usesBatches?"近期评论批次趋势":"评论发布时间趋势";
  $("#trend-note").textContent=hasHistory?`${recentHistory.length} 个采集日 · 每日自动更新`:usesBatches?`${buckets.length} 个等量时间批次 · 快照已积累 ${history.length}/7 天`:`覆盖 ${buckets.length} 个发布日期 · 快照已积累 ${history.length}/7 天`;
  const w=760,h=220,pad=28;
  const x = (i) => pad + i * ((w-pad*2)/Math.max(1,buckets.length-1)); const y = (rate) => h-pad-rate*(h-pad*2);
  const points = buckets.map((b,i) => `${x(i)},${y(b.rate)}`).join(" ");
  const area = `${pad},${h-pad} ${points} ${x(buckets.length-1)},${h-pad}`;
  $("#trend-chart").innerHTML = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="近期推荐率趋势">
    ${[0,.25,.5,.75,1].map(v=>`<line class="chart-grid" x1="${pad}" y1="${y(v)}" x2="${w-pad}" y2="${y(v)}"/><text class="chart-label" x="0" y="${y(v)+3}">${Math.round(v*100)}%</text>`).join("")}
    <polygon class="chart-area" points="${area}"/><polyline class="chart-line" points="${points}"/>
    ${buckets.map((b,i)=>`<circle class="chart-dot" cx="${x(i)}" cy="${y(b.rate)}" r="4"><title>${b.label}: ${pct(b.rate)} / ${b.count}条</title></circle>`).join("")}
    ${buckets.map((b,i)=> i%Math.ceil(buckets.length/5)===0 ? `<text class="chart-label" text-anchor="middle" x="${x(i)}" y="${h-5}">${b.label}</text>` : "").join("")}
  </svg>`;
}

function topicStats(game=state.game) {
  const totalNegative=game.reviews.filter(r=>!r.voted_up).length;
  return topics.map((topic) => { const all=game.reviews.filter(r=>r.topics.includes(topic.id)); const negative=all.filter(r=>!r.voted_up); return {...topic, all, negative, negativeRate: negative.length/Math.max(1,all.length),negativeShare:negative.length/Math.max(1,totalNegative)}; }).sort((a,b)=>b.negative.length-a.negative.length);
}

function renderTopics() {
  const stats=topicStats(), max=Math.max(...stats.map(s=>s.negative.length),1); if(!state.topic) state.topic=stats[0].id;
  $("#topic-bars").innerHTML=stats.map(item=>`<div class="topic-row"><button data-topic="${item.id}">${item.name}</button><div class="topic-volume"><div class="topic-track"><div class="topic-fill" style="width:${item.negative.length/max*100}%"></div></div><small>${item.all.length} 条</small></div><span class="topic-value ${item.all.length<30?"low-confidence":""}">${pct(item.negativeRate)}<small>${item.all.length<30?"小样本":"主题内"}</small></span><span class="topic-value">${pct(item.negativeShare)}<small>全部差评</small></span></div>`).join("");
  document.querySelectorAll("[data-topic]").forEach(button=>button.addEventListener("click",()=>{state.topic=button.dataset.topic;renderTopicDetail();})); renderTopicDetail();
}

function renderTopicDetail() {
  const item=topicStats().find(s=>s.id===state.topic); const sample=[...item.negative].sort((a,b)=>b.votes_up-a.votes_up)[0];
  $("#topic-detail").innerHTML=`<p class="kicker">SELECTED ISSUE</p><h3>${item.name}</h3><p>${item.description}</p><div class="topic-stat-grid"><div class="topic-stat"><strong>${item.all.length}</strong><span>主题提及</span></div><div class="topic-stat"><strong>${pct(item.negativeRate)}</strong><span>主题内负面率</span></div></div><p class="confidence-note">${confidenceText(item.all)}</p>${sample?`<div class="topic-stat evidence"><span>代表性原文 · ${sample.votes_up} 人认为有用</span><p>“${escapeHtml(sample.review.slice(0,180))}${sample.review.length>180?"…":""}”</p></div>`:""}<button id="view-topic-evidence" class="evidence-button" type="button">查看 ${item.all.length} 条相关证据 →</button>`;
  $("#view-topic-evidence")?.addEventListener("click",()=>{state.topicFilter=item.id;$("#topic-filter").value=item.id;state.page=1;renderReviews();document.querySelector("#reviews").scrollIntoView({behavior:"smooth"});});
}

function renderSegments() {
  const values=state.game.reviews.map(r=>r.playtime_at_review), q1=quantile(values,.25),q2=quantile(values,.5),q3=quantile(values,.75);
  const defs=[{label:"轻度玩家",note:`0—${hours(q1)}`,min:0,max:q1},{label:"普通玩家",note:`${hours(q1)}—${hours(q2)}`,min:q1,max:q2},{label:"深度玩家",note:`${hours(q2)}—${hours(q3)}`,min:q2,max:q3},{label:"核心玩家",note:`${hours(q3)}以上`,min:q3,max:Infinity}];
  $("#segment-grid").innerHTML=defs.map((def,index)=>{const items=state.game.reviews.filter(r=>r.playtime_at_review>=def.min&&(index===0?r.playtime_at_review<=def.max:r.playtime_at_review<def.max));return `<article class="segment ${items.length<30?"low-confidence-card":""}"><small>${def.label} · ${def.note}</small><strong>${pct(positiveRate(items))}</strong><span>${items.length} 条 · ${confidenceText(items)}</span><div class="segment-meter"><i style="width:${positiveRate(items)*100}%"></i></div></article>`;}).join("");
}

function renderLanguages() {
  const groups={}; state.game.reviews.forEach(r=>(groups[r.language]??=[]).push(r)); const rows=Object.entries(groups).sort((a,b)=>b[1].length-a[1].length).slice(0,8); const max=rows[0]?.[1].length||1;
  $("#language-table").innerHTML=rows.map(([language,items])=>`<div class="language-row ${items.length<30?"low-confidence-row":""}"><b>${languageNames[language]||language}</b><div class="bar"><i style="width:${items.length/max*100}%"></i></div><span>${items.length} 条</span><span title="${confidenceText(items)}">${pct(positiveRate(items))}${items.length<30?"*":""}</span></div>`).join("");
}

function renderInsights() {
  const stats=topicStats(); const top=stats[0]; const short=state.game.reviews.filter(r=>r.playtime_at_review<120); const long=state.game.reviews.filter(r=>r.playtime_at_review>=6000);
  const languageGroups=state.game.reviews.reduce((groups,review)=>{(groups[review.language]??=[]).push(review);return groups;},{});
  const langs=Object.entries(languageGroups).filter(([,items])=>items.length>=30).map(([lang,items])=>({lang,rate:positiveRate(items),count:items.length})).sort((a,b)=>a.rate-b.rate);
  const low=langs[0], high=langs.at(-1);
  const items=[
    `当前最集中的负面主题是“${top.name}”，命中 ${top.negative.length} 条差评。`,
    short.length >= 30 && long.length >= 30
      ? `评论时游玩不足 2 小时的玩家推荐率为 ${pct(positiveRate(short))}，100 小时以上玩家为 ${pct(positiveRate(long))}。`
      : `评论时游玩不足 2 小时的样本仅 ${short.length} 条，未达到 30 条门槛，暂不与长期玩家比较。`,
    low&&high?`${languageNames[low.lang]||low.lang}与${languageNames[high.lang]||high.lang}样本推荐率相差 ${Math.round((high.rate-low.rate)*100)} 个百分点。`:"语言样本不足，暂不判断地区差异。",
  ]; $("#insight-list").innerHTML=items.map(item=>`<li>${item}</li>`).join("");
}

function filteredReviews() {
  const query=$("#review-search").value.trim().toLowerCase(), sentiment=$("#sentiment-filter").value, language=$("#language-filter").value, topic=$("#topic-filter").value;
  return state.game.reviews.filter(r=>(!query||r.review.toLowerCase().includes(query))&&(sentiment==="all"||(sentiment==="positive")===r.voted_up)&&(language==="all"||r.language===language)&&(topic==="all"||r.topics.includes(topic))).sort((a,b)=>b.created-a.created);
}

function renderReviewFilters() {
  const langs=[...new Set(state.game.reviews.map(r=>r.language))].sort(); $("#language-filter").innerHTML=`<option value="all">全部语言</option>${langs.map(l=>`<option value="${l}">${languageNames[l]||l}</option>`).join("")}`;
  $("#topic-filter").innerHTML=`<option value="all">全部主题</option>${topics.map(topic=>`<option value="${topic.id}">${topic.name}</option>`).join("")}`;
  $("#topic-filter").value="all"; state.topicFilter="all";
}

function renderReviews() {
  const items=filteredReviews(), pages=Math.max(1,Math.ceil(items.length/state.pageSize)); state.page=Math.min(state.page,pages); const visible=items.slice((state.page-1)*state.pageSize,state.page*state.pageSize);
  $("#review-result-count").textContent=`${items.length} 条结果`; $("#page-state").textContent=`${state.page} / ${pages}`; $("#prev-page").disabled=state.page<=1; $("#next-page").disabled=state.page>=pages;
  $("#review-list").innerHTML=visible.map(r=>`<article class="review"><div class="review-sentiment ${r.voted_up?"positive":"negative"}">${r.voted_up?"推荐":"不推荐"}<br><small>${languageNames[r.language]||r.language}</small></div><p class="review-text">${escapeHtml(r.review)}</p><div class="review-meta">${dateText(r.created)}<br>评论时 ${hours(r.playtime_at_review)}<br>${r.votes_up} 人认为有用</div></article>`).join("")||`<article class="review"><p class="review-text">没有符合条件的评论。</p></article>`;
}

function renderQuality() {
  const quality=state.analysis.quality;
  const passed=quality.checks.filter(check=>check.passed).length;
  $("#quality-pass-count").textContent=`${passed} / ${quality.checks.length}`;
  $("#quality-checks").innerHTML=quality.checks.map(check=>`<div class="quality-check ${check.passed?"passed":"warning"}"><i>${check.passed?"✓":"!"}</i><span><b>${check.name}</b><small>${check.detail}</small></span></div>`).join("");
  const metrics=[
    ["分析可用评论",quality.analysis_ready_rows,`原始 ${quality.total_rows} 条 · 清洗移除 ${quality.removed_rows} 条`],
    ["精确重复",quality.exact_duplicate_rows,pct(quality.duplicate_rate)],
    ["极短评论",quality.short_text,pct(quality.short_rate)],
    ["主题覆盖",pct(quality.topic_coverage),"未覆盖部分待语义聚类"],
    ["语言覆盖",quality.language_count,"保留原始文本"],
  ];
  $("#quality-metrics").innerHTML=metrics.map(([label,value,note])=>`<article><small>${label}</small><strong>${value}</strong><span>${note}</span></article>`).join("");
  $("#quality-game-table").innerHTML=quality.games.map(game=>`<div class="quality-game-row"><b>${game.name}</b><span><small>样本</small>${game.rows}</span><span><small>推荐率</small>${pct(game.positive_rate)}</span><span><small>主题覆盖</small>${pct(game.topic_coverage)}</span><span><small>极短评论</small>${pct(game.short_rate)}</span></div>`).join("");
}

function renderModel() {
  const model=state.analysis.model, holdout=model.holdout;
  const uplift=holdout.accuracy-holdout.majority_baseline_accuracy;
  const metrics=[
    ["Accuracy",pct(holdout.accuracy),`较多数类基线 +${(uplift*100).toFixed(1)}pp`],
    ["Macro F1",holdout.macro_f1.toFixed(3),"兼顾推荐与不推荐"],
    ["Positive F1",holdout.f1.toFixed(3),`Precision ${holdout.precision.toFixed(3)}`],
    ["测试集",holdout.test_rows,`训练集 ${holdout.train_rows} 条`],
  ];
  $("#model-metrics").innerHTML=metrics.map(([label,value,note])=>`<article><small>${label}</small><strong>${value}</strong><span>${note}</span></article>`).join("");
  const [[tn,fp],[fn,tp]]=holdout.confusion_matrix;
  $("#confusion-matrix").innerHTML=`<div class="matrix-axis matrix-top">模型预测</div><div class="matrix-axis matrix-side">真实标签</div><div class="matrix-label"></div><div class="matrix-label">不推荐</div><div class="matrix-label">推荐</div><div class="matrix-label">不推荐</div><div class="matrix-cell correct"><strong>${tn}</strong><span>正确识别</span></div><div class="matrix-cell wrong"><strong>${fp}</strong><span>误判推荐</span></div><div class="matrix-label">推荐</div><div class="matrix-cell wrong"><strong>${fn}</strong><span>误判差评</span></div><div class="matrix-cell correct"><strong>${tp}</strong><span>正确识别</span></div>`;
  $("#cross-game-results").innerHTML=model.cross_game.map(item=>`<div class="cross-game-row"><span><b>${item.game}</b><small>${item.test_rows} 条完全留出</small></span><div><i style="width:${item.macro_f1*100}%"></i></div><strong>${item.macro_f1.toFixed(3)}</strong></div>`).join("");
  $("#error-list").innerHTML=model.errors.slice(0,8).map(error=>`<article class="model-error"><div><span class="error-label">真实：${error.actual?"推荐":"不推荐"}</span><span>预测：${error.predicted?"推荐":"不推荐"}</span></div><p>${escapeHtml(error.text)}</p><footer><span>${error.game} · ${languageNames[error.language]||error.language}</span><b>置信度 ${pct(error.confidence)}</b></footer></article>`).join("");
}

function selectGame(index) {
  state.game=state.data.games[index]; state.page=1; state.topic=null; renderGameIndex(); renderFocus(); renderMetrics(); renderComparison(); renderTrend(); renderTopics(); renderSegments(); renderLanguages(); renderInsights(); renderReviewFilters(); renderReviews();
}

async function init() {
  const [dataResponse,analysisResponse]=await Promise.all([
    fetch("data/steam-reviews.json",{cache:"no-store"}),
    fetch("data/model-analysis.json",{cache:"no-store"}),
  ]);
  if(!dataResponse.ok) throw new Error("无法读取评论数据"); if(!analysisResponse.ok) throw new Error("无法读取模型分析结果，请先运行 run-analysis.bat");
  state.data=await dataResponse.json(); state.analysis=await analysisResponse.json(); state.data.games.forEach(enrichGame);
  $("#generated-at").textContent=`数据更新 ${new Date(state.data.generated_at).toLocaleDateString("zh-CN")}`; $("#hero-description").textContent=`四款游戏、${state.data.games.reduce((sum,g)=>sum+g.reviews.length,0).toLocaleString()} 条公开评论的近期多语言口碑快照。`;
  renderQuality(); renderModel(); selectGame(0);
}

[$("#review-search"),$("#sentiment-filter"),$("#language-filter"),$("#topic-filter")].forEach(control=>control.addEventListener("input",()=>{state.page=1;state.topicFilter=$("#topic-filter").value;renderReviews();}));
$("#prev-page").addEventListener("click",()=>{state.page--;renderReviews();}); $("#next-page").addEventListener("click",()=>{state.page++;renderReviews();});
init().catch(error=>{document.body.innerHTML=`<main style="padding:40px;color:white"><h1>数据加载失败</h1><p>${escapeHtml(error.message)}</p><p>请通过 start.bat 启动，不要直接双击 HTML。</p></main>`;});
