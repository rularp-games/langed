/**
 * Перемещение фокуса стрелками внутри группы (вкладки, сегменты, меню).
 * Возвращает элемент, получивший фокус, либо null, если клавиша не навигационная.
 */
export function moveFocus(event, container, selector, { vertical = false } = {}) {
  const items = [...container.querySelectorAll(selector)].filter((el) => !el.disabled)
  if (!items.length) return null
  const index = items.indexOf(document.activeElement)
  const prevKeys = vertical ? ['ArrowUp'] : ['ArrowLeft', 'ArrowUp']
  const nextKeys = vertical ? ['ArrowDown'] : ['ArrowRight', 'ArrowDown']
  let target = null
  if (nextKeys.includes(event.key)) target = items[(index + 1) % items.length]
  else if (prevKeys.includes(event.key)) target = items[(index - 1 + items.length) % items.length]
  else if (event.key === 'Home') target = items[0]
  else if (event.key === 'End') target = items[items.length - 1]
  if (!target) return null
  event.preventDefault()
  target.focus()
  return target
}
