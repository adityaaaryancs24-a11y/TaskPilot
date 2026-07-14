# TaskPilot AI — Frontend

Mission Control dashboard for the TaskPilot AI platform.

## Features

- **Mission Control Dashboard**: Tasks, alerts, calendar, dependency graph
- **Daily Plan**: Top priorities with score breakdowns
- **All Tasks**: Full task list with filtering
- **AI Chat Assistant**: Natural language Q&A about tasks
- **Sources Dashboard**: Connector status and extraction visualization
- **Weekly Summary**: AI-generated weekly overview
- **Pipeline Traces**: Performance monitoring
- **Smart Settings**: API key management

## Tech Stack

- React 18 + TypeScript
- Vite 8
- Tailwind CSS v4
- shadcn/ui + Radix primitives
- Recharts (charts)
- React Flow (dependency graph)
- Framer Motion (animations)

## Setup

```bash
npm install
npm run dev
```

The dev server runs on port 5173 and proxies API calls to port 8000.

## Build

```bash
npm run build
```
