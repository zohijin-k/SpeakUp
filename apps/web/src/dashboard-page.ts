import { average, estimateSessionDuration, getDisplayAxisScores } from './report-utils';
import { getCompletedSessions } from './session-store';
import { computeGrowth, extractSessionMetrics } from './growth-metrics';

declare const Chart: any;

const TYPE_LABEL: Record<string, string> = {
  presentation: '발표',
  interview: '면접',
  negotiation: '협상',
  persuasion: '설득',
  daily: '일상 대화',
  phone: '전화',
  online: '온라인',
  free: '자유 연습',
};

function setMetric(key: string, value: string, note: string) {
  const valueEl = document.querySelector<HTMLElement>(`[data-metric="${key}"]`);
  const noteEl = document.querySelector<HTMLElement>(`[data-metric-note="${key}"]`);
  if (valueEl) valueEl.textContent = value;
  if (noteEl) noteEl.textContent = note;
}

function computeStreak(days: string[]): number {
  if (days.length === 0) return 0;
  const unique = [...new Set(days)].sort().reverse();
  let streak = 0;
  let cursor = new Date(unique[0]);
  for (const day of unique) {
    const current = new Date(day);
    if (current.toDateString() === cursor.toDateString()) {
      streak += 1;
      cursor.setDate(cursor.getDate() - 1);
    } else {
      break;
    }
  }
  return streak;
}

function renderChart() {
  const sessions = getCompletedSessions().slice().reverse();
  const canvas = document.getElementById('growth-chart') as HTMLCanvasElement | null;
  if (!canvas || sessions.length === 0) return;
  const labels = sessions.map((_, index) => `${index + 1}회`);
  const overall = sessions.map((session) => Number(session.report.accuracy_overall.toFixed(1)));
  const verbal = sessions.map((session) => getDisplayAxisScores(session.report).verbal ?? null);
  const prosody = sessions.map((session) => getDisplayAxisScores(session.report).prosody ?? null);
  const nonverbal = sessions.map((session) => getDisplayAxisScores(session.report).nonverbal ?? null);

  new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: '전체', data: overall, borderColor: '#AFCBFF', backgroundColor: '#AFCBFF', borderWidth: 2.2, tension: 0.28 },
        { label: '언어', data: verbal, borderColor: '#F3C9D0', borderDash: [4, 4], borderWidth: 1.8, tension: 0.28 },
        { label: '준언어', data: prosody, borderColor: '#F6E6A8', borderDash: [4, 4], borderWidth: 1.8, tension: 0.28 },
        { label: '비언어', data: nonverbal, borderColor: '#CDEEE7', borderDash: [4, 4], borderWidth: 1.8, tension: 0.28 },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 0, max: 100, grid: { color: 'rgba(151, 165, 188, 0.18)' } },
        x: { grid: { display: false } },
      },
    },
  });
}

function renderGrowthSummary() {
  const card = document.getElementById('growth-summary');
  const grid = document.getElementById('growth-grid');
  const caption = document.getElementById('growth-caption');
  if (!card || !grid) return;

  const sessions = getCompletedSessions();
  const deltas = computeGrowth(sessions);
  if (deltas.length === 0) return; // 세션 2개 미만 — 카드 숨김 유지

  card.hidden = false;
  if (caption) caption.textContent = `1회차 → ${sessions.length}회차 실측 비교`;
  grid.innerHTML = deltas
    .map((delta) => {
      const tone = delta.improved === null ? 'is-flat' : delta.improved ? 'is-up' : 'is-down';
      return `
        <div class="growth-item ${tone}">
          <span class="growth-label">${delta.label}</span>
          <strong class="growth-delta">${delta.deltaText}</strong>
          <span class="growth-range">${delta.firstText} → ${delta.latestText}</span>
        </div>
      `;
    })
    .join('');
}

// 습관 카드 — 실측 지표를 세션별 막대로 (최근 8세션, 과거→최신).
const HABIT_BAR_COLORS = ['#AFCBFF', '#CDEEE7', '#F3C9D0', '#F6E6A8'];

function renderHabits() {
  const sessions = getCompletedSessions().slice(0, 8).reverse();
  if (sessions.length === 0) return;
  const metrics = sessions.map((session) => extractSessionMetrics(session));
  const latest = metrics[metrics.length - 1];

  const configs = [
    {
      key: 'filler',
      // 필러/분 → 적을수록 좋음: 0회=100, 4회/분 이상=바닥
      values: metrics.map((m) => (m.fillersPerMin === null ? 0 : Math.max(8, 100 - m.fillersPerMin * 25))),
      titles: metrics.map((m) => (m.fillersPerMin === null ? '전사 없음' : `${m.fillersPerMin}회/분`)),
      note: latest.fillersPerMin === null ? '전사 데이터가 없어요.' : `최근 세션 필러 ${latest.fillersPerMin}회/분`,
    },
    {
      key: 'delivery',
      // 안정 구간(110~160wpm) 근접도
      values: metrics.map((m) => (m.wpm === null ? 0 : Math.max(8, 100 - Math.abs(m.wpm - 135) * 1.5))),
      titles: metrics.map((m) => (m.wpm === null ? '전사 없음' : `${m.wpm} wpm`)),
      note: latest.wpm === null ? '전사 데이터가 없어요.' : `최근 평균 ${latest.wpm} wpm`,
    },
    {
      key: 'gaze',
      values: metrics.map((m) => m.gazeScore ?? 0),
      titles: metrics.map((m) => (m.gazeScore === null ? '측정 없음' : `${Math.round(m.gazeScore)}점`)),
      note: latest.gazeScore === null ? '시선 데이터가 없어요.' : `최근 시선 안정 ${Math.round(latest.gazeScore)}점`,
    },
    {
      key: 'silence',
      // 긴 침묵 횟수 → 적을수록 좋음
      values: metrics.map((m) => Math.max(8, 100 - m.silenceCount * 18)),
      titles: metrics.map((m) => `긴 침묵 ${m.silenceCount}회`),
      note: `최근 세션 긴 침묵 ${latest.silenceCount}회`,
    },
  ];

  configs.forEach((config) => {
    const card = document.querySelector<HTMLElement>(`[data-habit="${config.key}"]`);
    if (!card) return;
    const list = card.querySelector<HTMLElement>('.bar-list');
    if (list) {
      list.innerHTML = config.values
        .map((value, index) => {
          const height = Math.max(0, Math.min(100, value));
          const color = HABIT_BAR_COLORS[index % HABIT_BAR_COLORS.length];
          return `<i style="height: ${height}%; background: ${color}" title="${index + 1}회차 · ${config.titles[index]}"></i>`;
        })
        .join('');
    }
    const note = card.querySelector<HTMLElement>('p');
    if (note) note.textContent = config.note;
  });
}

function renderScenarioBreakdown() {
  const container = document.getElementById('scenario-breakdown');
  if (!container) return;
  const sessions = getCompletedSessions();
  if (sessions.length === 0) return;

  const scores = new Map<string, number[]>();
  sessions.forEach((session) => {
    const key = session.situation || TYPE_LABEL[session.type] || session.type || '기타';
    const row = scores.get(key) ?? [];
    row.push(session.report.accuracy_overall);
    scores.set(key, row);
  });

  container.innerHTML = [...scores.entries()]
    .slice(0, 4)
    .map(([label, values]) => {
      const score = average(values) ?? 0;
      return `
        <div class="axis-row">
          <span class="axis-label">${label}</span>
          <span class="axis-bar"><span class="axis-fill" style="width: ${Math.round(score)}%"></span></span>
          <span class="axis-score">${Math.round(score)}</span>
        </div>
      `;
    })
    .join('');
}

function renderRecentSessions() {
  const container = document.getElementById('recent-sessions');
  if (!container) return;
  const sessions = getCompletedSessions().slice(0, 6);
  if (sessions.length === 0) return;
  container.innerHTML = sessions
    .map(
      (session) => `
        <a href="report.html?session=${encodeURIComponent(session.sessionId)}">
          <i class="ti ti-clock-hour-4"></i>
          <span>${session.project}</span>
          <em>${Math.round(session.report.accuracy_overall)}</em>
        </a>
      `,
    )
    .join('');
}

function renderMetrics() {
  const sessions = getCompletedSessions();
  if (sessions.length === 0) return;
  const avgScore = average(sessions.map((session) => session.report.accuracy_overall)) ?? 0;
  const totalMinutes = sessions.reduce((sum, session) => sum + estimateSessionDuration(session.report), 0) / 60;
  const streak = computeStreak(sessions.map((session) => session.createdAt.slice(0, 10)));

  setMetric('average', `${Math.round(avgScore)}`, '최근 연습 전체 평균이에요.');
  setMetric('sessions', `${sessions.length}`, '지금까지 쌓인 연습 세션 수예요.');
  setMetric('time', `${Math.round(totalMinutes)}m`, '누적 연습 시간 기준이에요.');
  setMetric('streak', `${streak}일`, '연속으로 연습한 흐름이에요.');

  const latest = sessions[0];
  const goalCopy = document.getElementById('goal-banner-copy');
  const goalMeter = document.getElementById('goal-banner-meter');
  if (goalCopy) {
    const firstDrill = latest.report.training_prescriptions[0];
    goalCopy.textContent = firstDrill
      ? `${firstDrill.title}에 집중해보세요. ${firstDrill.steps[0] ?? firstDrill.addresses}`
      : latest.report.improvements[0]?.text || '가장 최근 세션의 개선 포인트를 다음 목표로 이어가보세요.';
  }
  if (goalMeter) {
    goalMeter.style.width = `${Math.round(latest.report.accuracy_overall)}%`;
  }
}

// 한 구획이 실패해도(예: 차트 CDN 미로딩) 나머지 구획은 계속 그린다.
function safe(name: string, fn: () => void) {
  try {
    fn();
  } catch (error) {
    console.error(`[dashboard] ${name} 렌더 실패`, error);
  }
}

function render() {
  safe('metrics', renderMetrics);
  safe('growth-summary', renderGrowthSummary);
  safe('chart', renderChart);
  safe('habits', renderHabits);
  safe('scenario', renderScenarioBreakdown);
  safe('recent', renderRecentSessions);
}

void render();
