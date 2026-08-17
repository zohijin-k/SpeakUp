// 세션 간 성장 지표 — liveEvents(실시간 코칭 이벤트)와 전사(subtitle)에서
// 원시 지표를 뽑아 세션끼리 비교한다. 대시보드의 "첫 세션 대비 성장" 카드와
// 습관 카드가 이 모듈을 사용한다.
//
// 지표 출처:
// - wpm            : 전사(subtitle_segments) 단어 수 / 세션 길이 → 실제 평균 말 속도
// - fillersPerMin  : filler_burst 이벤트의 감지 횟수 합 / 분
// - gazeScore      : 리포트 gaze 축 점수 (0-100)
// - silenceCount   : silence_long 이벤트 횟수
// - overall        : 리포트 종합 점수

import type { CompletedSession } from './session-store';
import { estimateSessionDuration, getAxisScore } from './report-utils';

export interface SessionMetrics {
  wpm: number | null;
  fillersPerMin: number | null;
  gazeScore: number | null;
  silenceCount: number;
  overall: number;
  durationMin: number;
}

const IDEAL_WPM = 135; // 안정 구간(110~160)의 중심 — 근접할수록 좋다.

function transcriptWordCount(session: CompletedSession): number | null {
  const segments = session.report.subtitle_segments;
  if (!segments || segments.length === 0) return null;
  return segments.reduce((sum, segment) => {
    if (segment.words && segment.words.length > 0) return sum + segment.words.length;
    return sum + segment.text.split(/\s+/).filter(Boolean).length;
  }, 0);
}

export function extractSessionMetrics(session: CompletedSession): SessionMetrics {
  const durationSec = Math.max(1, estimateSessionDuration(session.report));
  const durationMin = durationSec / 60;
  const events = session.liveEvents ?? [];

  const words = transcriptWordCount(session);
  const wpm = words !== null && durationMin > 0.2 ? words / durationMin : null;

  const fillerHits = events
    .filter((event) => event.key === 'filler_burst')
    .reduce((sum, event) => sum + (typeof event.value === 'number' ? event.value : 1), 0);
  const fillersPerMin = durationMin > 0.2 ? fillerHits / durationMin : null;

  const silenceCount = events.filter((event) => event.key === 'silence_long').length;

  return {
    wpm: wpm !== null ? Math.round(wpm) : null,
    fillersPerMin: fillersPerMin !== null ? Number(fillersPerMin.toFixed(1)) : null,
    gazeScore: getAxisScore(session.report, 'gaze'),
    silenceCount,
    overall: session.report.accuracy_overall,
    durationMin,
  };
}

export interface GrowthDelta {
  key: string;
  label: string;
  firstText: string;
  latestText: string;
  deltaText: string;
  improved: boolean | null; // null = 변화 없음/판단 불가
}

function percentChange(first: number, latest: number): number | null {
  if (first === 0) return null;
  return ((latest - first) / first) * 100;
}

/**
 * sessions는 최신순(session-store 기본 정렬)으로 받는다.
 * 첫 세션 vs 가장 최근 세션을 비교해 지표별 변화를 만든다.
 * 세션이 2개 미만이면 빈 배열.
 */
export function computeGrowth(sessions: CompletedSession[]): GrowthDelta[] {
  if (sessions.length < 2) return [];
  const latest = extractSessionMetrics(sessions[0]);
  const first = extractSessionMetrics(sessions[sessions.length - 1]);
  const deltas: GrowthDelta[] = [];

  if (first.fillersPerMin !== null && latest.fillersPerMin !== null) {
    const change = percentChange(first.fillersPerMin, latest.fillersPerMin);
    deltas.push({
      key: 'filler',
      label: '필러 표현',
      firstText: `${first.fillersPerMin}회/분`,
      latestText: `${latest.fillersPerMin}회/분`,
      deltaText:
        change === null
          ? latest.fillersPerMin === 0
            ? '유지'
            : `+${latest.fillersPerMin}회/분`
          : `${change <= 0 ? '▼' : '▲'} ${Math.abs(Math.round(change))}%`,
      improved: change === null ? latest.fillersPerMin === 0 : change < 0,
    });
  }

  if (first.wpm !== null && latest.wpm !== null) {
    const firstGap = Math.abs(first.wpm - IDEAL_WPM);
    const latestGap = Math.abs(latest.wpm - IDEAL_WPM);
    deltas.push({
      key: 'wpm',
      label: '말 속도',
      firstText: `${first.wpm} wpm`,
      latestText: `${latest.wpm} wpm`,
      deltaText: latestGap < firstGap ? '안정 구간 근접' : latestGap === firstGap ? '유지' : '변동 커짐',
      improved: latestGap < firstGap ? true : latestGap === firstGap ? null : false,
    });
  }

  if (first.gazeScore !== null && latest.gazeScore !== null) {
    const diff = Math.round(latest.gazeScore - first.gazeScore);
    deltas.push({
      key: 'gaze',
      label: '시선 안정',
      firstText: `${Math.round(first.gazeScore)}점`,
      latestText: `${Math.round(latest.gazeScore)}점`,
      deltaText: diff === 0 ? '유지' : `${diff > 0 ? '▲' : '▼'} ${Math.abs(diff)}점`,
      improved: diff === 0 ? null : diff > 0,
    });
  }

  {
    const diff = Math.round(latest.overall - first.overall);
    deltas.push({
      key: 'overall',
      label: '종합 점수',
      firstText: `${Math.round(first.overall)}점`,
      latestText: `${Math.round(latest.overall)}점`,
      deltaText: diff === 0 ? '유지' : `${diff > 0 ? '▲' : '▼'} ${Math.abs(diff)}점`,
      improved: diff === 0 ? null : diff > 0,
    });
  }

  return deltas;
}
