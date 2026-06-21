import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldCheck, ChevronRight, Check } from 'lucide-react'

const STEPS = [
  {
    title: "Welcome to ISRO ISTRAC SOC",
    description: "Your platform for advanced threat detection and AI-assisted investigation. Let's take a quick tour to get you started.",
    action: "Start Tour",
    icon: "🚀"
  },
  {
    title: "Dashboard Overview",
    description: "Get a high-level view of active incidents, open alerts, and global SLA compliance across the infrastructure.",
    action: "Next",
    icon: "📊"
  },
  {
    title: "Investigating Alerts",
    description: "Review automated SHAP explanations, temporal baselines, and cross-model consensus matrices directly from the alert queue.",
    action: "Next",
    icon: "🔍"
  },
  {
    title: "AI Investigation Assistant",
    description: "Leverage the local Small Language Model (SLM) for guided playbooks and complex query generation.",
    action: "Next",
    icon: "🤖"
  },
  {
    title: "Labeling & Feedback",
    description: "Label uncertain alerts as True Positive or False Positive. Your feedback continuously retrains the active models.",
    action: "Finish Tour",
    icon: "🏷️"
  }
]

export function OnboardingWizard() {
  const [isOpen, setIsOpen] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    const hasOnboarded = localStorage.getItem('soc-onboarded')
    if (!hasOnboarded) {
      setIsOpen(true)
    }
  }, [])

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(c => c + 1)
    } else {
      localStorage.setItem('soc-onboarded', 'true')
      setIsOpen(false)
      navigate('/dashboard')
    }
  }

  const handleSkip = () => {
    localStorage.setItem('soc-onboarded', 'true')
    setIsOpen(false)
  }

  if (!isOpen) return null

  const step = STEPS[currentStep]

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-500">
      <div className="bg-[var(--bg_primary)] w-full max-w-lg rounded-2xl border border-[var(--border)] shadow-2xl p-8 relative overflow-hidden transform animate-in zoom-in-95 duration-300">
        
        {/* Progress bar */}
        <div className="absolute top-0 left-0 w-full h-1 bg-[var(--bg_secondary)]">
          <div 
            className="h-full bg-blue-500 transition-all duration-300 ease-out" 
            style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        <div className="flex flex-col items-center text-center space-y-6 mt-4">
          <div className="w-20 h-20 bg-[var(--bg_secondary)] border border-[var(--border)] rounded-full flex items-center justify-center text-4xl shadow-inner">
            {step.icon}
          </div>
          
          <div>
            <h2 className="text-2xl font-bold text-[var(--text_primary)] mb-2">{step.title}</h2>
            <p className="text-[var(--text_secondary)] leading-relaxed">{step.description}</p>
          </div>

          <div className="flex items-center gap-4 w-full pt-4">
            <button 
              onClick={handleSkip}
              className="text-sm font-medium text-[var(--text_secondary)] hover:text-[var(--text_primary)] transition-colors px-4 py-2"
            >
              Skip Tour
            </button>
            <button 
              onClick={handleNext}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white rounded-xl py-3 font-bold shadow-lg shadow-blue-500/20 transition-all flex items-center justify-center gap-2 group"
            >
              {step.action}
              {currentStep < STEPS.length - 1 ? (
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              ) : (
                <Check className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        <div className="mt-8 flex justify-center gap-2">
          {STEPS.map((_, i) => (
            <div 
              key={i} 
              className={`w-2 h-2 rounded-full transition-colors ${i === currentStep ? 'bg-blue-500' : 'bg-gray-700'}`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
