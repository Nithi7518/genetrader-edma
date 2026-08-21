import { useState, useEffect } from 'react'
import { Activity, Play, Zap, Database, ArrowUpRight, TrendingUp } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import './App.css'

function App() {
  const [taskId, setTaskId] = useState(null)
  const [status, setStatus] = useState("IDLE")
  const [progress, setProgress] = useState(null)
  const [result, setResult] = useState(null)
  const [livePrices, setLivePrices] = useState({})
  const [top10, setTop10] = useState([])

  useEffect(() => {
    // Connect to WebSocket for live trading data
    const ws = new WebSocket("ws://localhost:8000/api/live")
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.prices) setLivePrices(data.prices)
        if (data.top_10) setTop10(data.top_10)
      } catch (e) {
        console.error("WS Parse error", e)
      }
    }

    return () => ws.close()
  }, [])

  const startOptimization = async () => {
    try {
      setStatus("STARTING")
      const res = await fetch("http://localhost:8000/api/start", { method: 'POST' })
      const data = await res.json()
      setTaskId(data.task_id)
      setStatus("RUNNING")
    } catch (e) {
      console.error(e)
      setStatus("ERROR")
    }
  }

  useEffect(() => {
    let interval = null
    if (status === "RUNNING" && taskId) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`http://localhost:8000/api/status/${taskId}`)
          const data = await res.json()
          
          if (data.progress) {
            setProgress(prev => {
              const chartData = prev ? [...prev.chartData] : []
              if (data.progress.generation !== (prev?.generation || -1)) {
                chartData.push({
                  generation: data.progress.generation,
                  fitness: parseFloat(data.progress.fitness.toFixed(4))
                })
              }
              return {
                ...data.progress,
                chartData
              }
            })
          }

          if (data.task_status === "SUCCESS") {
            setStatus("COMPLETED")
            setResult(data.task_result)
            clearInterval(interval)
          } else if (data.task_status === "FAILURE") {
            setStatus("ERROR")
            clearInterval(interval)
          }
        } catch (e) {
          console.error(e)
        }
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [status, taskId])

  const startSimulation = () => {
      setStatus("RUNNING")
      let gen = 0
      let currentFitness = 1.2
      const chartData = []
      const interval = setInterval(() => {
        gen += 1
        currentFitness += Math.random() * 0.1
        chartData.push({ generation: gen, fitness: parseFloat(currentFitness.toFixed(4)) })
        
        setProgress({
          generation: gen,
          maxGenerations: 30,
          fitness: currentFitness,
          chartData: [...chartData]
        })

        if (gen >= 30) {
          clearInterval(interval)
          setStatus("COMPLETED")
          setResult({
            best_chromosome: [0.0, 14.2, 50.1, 14.0, 31.0, 71.5, 0.03, 0.12, 0.0],
            fitness: currentFitness,
            sharpe_ratio: currentFitness,
            strategy: "RSI_MACD"
          })
        }
      }, 500)
  }

  return (
    <div className="layout">
      <header className="navbar">
        <div className="nav-container">
          <div className="nav-logo">
            <Zap size={20} className="icon-emerald" />
            <h1>GeneTrader <span className="dim">EDMA</span></h1>
          </div>
          <div className="nav-status">
            <div className="status-badge"><Database size={14}/> Redis Online</div>
            <div className="status-badge"><Activity size={14}/> WS Connected</div>
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="dashboard-grid">
          
          {/* Left Column: AI Engine Controls */}
          <aside className="sidebar">
            <div className="card control-panel">
              <div className="card-header">
                <h2>AI Optimization Engine</h2>
                <p>Distributed genetic algorithm workers.</p>
              </div>

              <div className="system-status">
                <span className="label">GA Status</span>
                <span className={`badge ${status.toLowerCase()}`}>
                  {status === 'RUNNING' && <div className="pulse-dot"/>}
                  {status}
                </span>
              </div>

              <div className="button-group">
                <button 
                  onClick={startOptimization}
                  disabled={status === "RUNNING"}
                  className="btn-primary"
                >
                  <Play size={16} /> Evolve New Strategy
                </button>
                <button 
                  onClick={startSimulation}
                  disabled={status === "RUNNING"}
                  className="btn-secondary"
                >
                  <TrendingUp size={16} /> Run Mock Sim
                </button>
              </div>
            </div>

            {/* Trajectory Chart embedded in sidebar for space efficiency */}
            <div className="card chart-panel">
              <div className="chart-header">
                <div>
                  <h2>Fitness Trajectory</h2>
                </div>
                {progress && (
                  <div className="chart-stats text-right">
                    <div className="current-fitness">{progress.fitness.toFixed(3)}</div>
                  </div>
                )}
              </div>
              <div className="mini-chart-container">
                {!progress ? (
                  <div className="empty-state">
                    <p>Awaiting run</p>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={150}>
                    <LineChart data={progress.chartData}>
                      <YAxis domain={['auto', 'auto']} hide/>
                      <Tooltip contentStyle={{ backgroundColor: '#111', border: '1px solid #333' }} itemStyle={{ color: '#10b981' }}/>
                      <Line type="monotone" dataKey="fitness" stroke="#10b981" strokeWidth={2} dot={false} isAnimationActive={false}/>
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </aside>

          {/* Right Column: Live Markets */}
          <section className="markets-area">
            
            {/* Top 10 Recommendations Panel */}
            <div className="section-title">
                <h2>Top 10 AI Recommendations</h2>
                <span className="live-pulse">Live</span>
            </div>
            
            <div className="top-10-grid">
              {top10.length > 0 ? top10.map((signal, idx) => (
                <div key={idx} className="top-10-card">
                  <div className="top-10-header">
                    <span className="rank">#{idx + 1}</span>
                    <span className="symbol">{signal.symbol}</span>
                  </div>
                  <div className="top-10-body">
                    <div className="confidence">
                      <span className="conf-value">{signal.confidence.toFixed(1)}%</span>
                      <span className="conf-label">Expected ROI Score</span>
                    </div>
                    <div className="action-tag">
                      <ArrowUpRight size={16} /> BUY
                    </div>
                  </div>
                  <div className="top-10-footer">
                    Evolved {signal.strategy}
                  </div>
                </div>
              )) : (
                <div className="empty-recommendations">
                    Waiting for AI signals... Make sure to run an evolution first.
                </div>
              )}
            </div>

            {/* All Stocks Grid (Groww Style) */}
            <div className="section-title mt-xl">
                <h2>Live Market Overview</h2>
            </div>
            
            <div className="stocks-grid">
              {Object.entries(livePrices).length > 0 ? (
                Object.entries(livePrices).map(([sym, data]) => {
                  const price = typeof data.price === 'number' ? data.price : parseFloat(data.price);
                  const change = typeof data.change === 'number' ? data.change : parseFloat(data.change);
                  const isPositive = change >= 0;
                  
                  return (
                    <div key={sym} className="stock-card">
                      <h3 className="stock-sym">{sym}</h3>
                      <div className="stock-price">${price.toFixed(2)}</div>
                      <div className={`stock-change ${isPositive ? 'positive' : 'negative'}`}>
                        {isPositive ? '+' : ''}{change.toFixed(2)}%
                      </div>
                    </div>
                  )
                })
              ) : (
                <div className="empty-recommendations">Loading live market data...</div>
              )}
            </div>

          </section>

        </div>
      </main>
    </div>
  )
}

export default App
