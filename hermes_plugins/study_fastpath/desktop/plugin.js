import { atom, host, useValue } from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'

const state = atom({ session: null, timer: null })
const clock = atom(Date.now())
let lastAutoOpenedTimer = null
let notifiedTimer = null

function remaining(timer, now) {
  if (!timer) return null
  if (timer.status !== 'running' || !timer.deadline) return timer.remaining_seconds
  return Math.max(0, Math.ceil((Date.parse(timer.deadline) - now) / 1000))
}

function format(seconds) {
  if (seconds == null) return '—'
  const mins = Math.floor(seconds / 60)
  return `${String(mins).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}

function TimerPanel({ act }) {
  const value = useValue(state)
  const now = useValue(clock)
  const timer = value.timer
  const seconds = remaining(timer, now)
  const running = timer?.status === 'running'
  const active = running && seconds > 0
  const paused = timer?.status === 'paused'
  return jsxs('div', {
    className: 'flex h-full min-h-64 flex-col gap-4 p-5 text-(--ui-text-primary)',
    children: [
      jsxs('header', { className: 'flex items-start justify-between gap-3', children: [
        jsxs('div', { children: [
          jsx('div', { className: 'text-xs text-(--ui-text-tertiary)', children: 'SESIÓN DE ESTUDIO' }),
          jsx('h2', { className: 'mt-1 text-lg font-semibold', children: value.session?.subject_name || 'Sin sesión abierta' }),
          value.session?.id ? jsx('div', { className: 'text-xs text-(--ui-text-tertiary)', children: `Sesión #${value.session.id}` }) : null
        ] }),
        jsx('button', { type: 'button', onClick: () => act('end_session'), disabled: !value.session,
          className: 'rounded-md border border-(--ui-border) px-2.5 py-1.5 text-xs disabled:opacity-40', children: 'Cerrar sesión' })
      ] }),
      jsxs('section', { className: 'rounded-xl border border-(--ui-border) bg-(--ui-bg-secondary) p-5 text-center', children: [
        jsx('div', { className: 'font-mono text-5xl font-semibold tabular-nums tracking-tight', children: format(seconds) }),
        jsx('div', { className: 'mt-2 text-sm text-(--ui-text-secondary)', children: active ? 'Timer en curso' : paused ? 'Timer pausado' : timer?.status === 'finished' || (running && seconds === 0) ? 'Bloque completado' : timer?.status === 'cancelled' ? 'Timer detenido' : 'Sin timer activo' }),
        timer?.label ? jsx('div', { className: 'mt-1 text-xs text-(--ui-text-tertiary)', children: timer.label }) : null
      ] }),
      jsxs('div', { className: 'flex flex-wrap gap-2', children: [
        active && value.session?.status === 'active' ? jsx('button', { type: 'button', onClick: () => act('pause'), className: 'rounded-md bg-(--ui-accent) px-3 py-2 text-sm text-white', children: 'Pausar timer' }) : null,
        paused && value.session?.status === 'active' ? jsx('button', { type: 'button', onClick: () => act('resume'), className: 'rounded-md bg-(--ui-accent) px-3 py-2 text-sm text-white', children: 'Reanudar timer' }) : null,
        active || paused ? jsx('button', { type: 'button', onClick: () => act('stop'), className: 'rounded-md border border-(--ui-border) px-3 py-2 text-sm', children: 'Detener timer' }) : null
      ] }),
      value.session?.status === 'active' ? jsx('button', { type: 'button', onClick: () => act('pause_session'), className: 'self-start rounded-md border border-(--ui-border) px-3 py-2 text-sm', children: 'Pausar sesión' }) : null,
      value.session?.status === 'paused' ? jsx('button', { type: 'button', onClick: () => act('resume_session'), className: 'self-start rounded-md border border-(--ui-border) px-3 py-2 text-sm', children: 'Reanudar sesión' }) : null,
      value.session?.status === 'active' && !active && !paused ? jsx('form', {
        className: 'flex items-center gap-2',
        onSubmit: event => {
          event.preventDefault()
          const minutes = Number(new FormData(event.currentTarget).get('minutes'))
          if (Number.isInteger(minutes) && minutes > 0) act('start', minutes)
        },
        children: [
          jsx('input', { name: 'minutes', type: 'number', min: 1, max: 1440, defaultValue: 25, required: true,
            className: 'w-24 rounded-md border border-(--ui-border) bg-(--ui-bg-primary) px-3 py-2 text-sm', 'aria-label': 'Duración del timer en minutos' }),
          jsx('button', { type: 'submit', className: 'rounded-md bg-(--ui-accent) px-3 py-2 text-sm text-white', children: 'Iniciar bloque' })
        ]
      }) : null,
      jsx('p', { className: 'mt-auto text-xs text-(--ui-text-tertiary)', children: 'Los bloques se guardan dentro de esta sesión. Cerrar un timer no cierra la sesión.' })
    ]
  })
}

function TimerChip({ openPanel }) {
  const value = useValue(state)
  const now = useValue(clock)
  const seconds = remaining(value.timer, now)
  return jsx('button', {
    type: 'button', onClick: openPanel,
    className: 'px-2 text-xs tabular-nums text-(--ui-text-secondary)',
    title: 'Abrir timer de estudio',
    children: value.timer?.status === 'running' ? `⏱ ${format(seconds)}` : '⏱ Study'
  })
}

export default {
  id: 'study-fastpath',
  name: 'Study Timer',
  register(ctx) {
    const load = async () => {
      try {
        const next = await ctx.rest('/timer')
        state.set(next)
        const timer = next?.timer
        if (timer?.status === 'running' && timer.id !== lastAutoOpenedTimer) {
          lastAutoOpenedTimer = timer.id
          openPanel()
        }
      } catch { /* The agent-side plugin may be disabled or the gateway disconnected. */ }
    }
    const openPanel = () => {
      if (typeof host.openWorkspace === 'function') {
        host.openWorkspace('study-fastpath-timer', {
          title: 'Timer de estudio', minWidth: '320px',
          render: () => jsx(TimerPanel, { act })
        })
      } else {
        host.notify({ kind: 'info', message: 'Timer activo. Abrí el panel Study Timer para verlo.' })
      }
    }
    const act = async (action, duration_minutes) => {
      try {
        state.set(await ctx.rest('/timer/action', { method: 'POST', body: { action, duration_minutes } }))
        if (action === 'start' || action === 'resume') openPanel()
      } catch (error) {
        host.notifyError(error, 'No se pudo actualizar el timer.')
      }
    }

    ctx.register({
      id: 'timer-chip', area: 'statusBar.right', order: 120,
      render: () => jsx(TimerChip, { openPanel })
    })
    ctx.register({
      id: 'timer-pane', area: 'panes', title: 'Study Timer',
      data: { placement: 'right', width: '330px' },
      render: () => jsx(TimerPanel, { act })
    })
    ctx.onEvent('tool.complete', event => {
      const payload = event?.payload || event
      if (payload?.name === 'study_timer_start' || payload?.name === 'study_timer_resume') {
        void load().then(() => {
          if (state.get().timer?.status === 'running') openPanel()
        })
      }
    })
    const refresh = setInterval(() => { void load() }, 5000)
    const tick = setInterval(() => {
      const now = Date.now()
      clock.set(now)
      const timer = state.get().timer
      if (timer?.status === 'running' && remaining(timer, now) === 0 && notifiedTimer !== timer.id) {
        notifiedTimer = timer.id
        host.notify({ kind: 'info', title: 'Timer terminado', message: 'Terminó el bloque de estudio.' })
        void load()
      }
    }, 1000)
    ctx.onDispose(() => { clearInterval(refresh); clearInterval(tick) })
    void load()
  }
}
