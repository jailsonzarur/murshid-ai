# Project Instructions

This is a Vite + React + TypeScript project. Keep React code typed, component-focused, and compatible with the existing build and lint configuration.

## React Practices

- Prefer small reusable components with explicit props.
- Keep component modules self-contained and avoid unnecessary module-level mutable state.
- Use direct imports from the concrete file path instead of introducing barrel files.
- Avoid defining components inside other components.
- Derive render values during render instead of mirroring them into state.
- Use functional state updates when the next value depends on the previous value.
- Keep effects for synchronization with external systems, not for basic derived UI state.

## Design System

- Use the Liquid Glass primitives in `src/components/ui/*` before creating new local controls.
- Use `src/theme/liquid-glass.ts` for shared colors, radii, shadows, and blur tokens.
- Use `src/lib/cn.ts` for class name composition.
- Keep primitives accessible: native controls where possible, labels for inputs/search, and semantic buttons.
- Do not add Tailwind-only class names unless Tailwind is configured in the project.

## Quality

- Run `npm run build` after TypeScript or component changes when feasible.
- Keep changes scoped to the requested behavior and avoid unrelated formatting churn.
