import { defineConfig } from 'vitest/config'

export default defineConfig({
  // Sans cela, le JSX des composants est compilé en React.createElement et
  // tout test qui rend un composant échoue sur « React is not defined ».
  esbuild: { jsx: 'automatic' },
  test: {
    environment: 'node',
    include: ['src/**/*.test.{js,jsx}'],
  },
})
