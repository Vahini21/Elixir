use client

import type React from react

import { useState, useRef, useEffect } from react
import Header from @componentsheader
import Footer from @componentsfooter
import { Button } from @componentsuibutton
import { Card, CardContent, CardHeader, CardTitle } from @componentsuicard
import { useLanguage } from @applanguage-context
import { useAuth } from @appauth-provider
import { useRouter } from nextnavigation
import { Upload, File, X, Loader2, CheckCircle, AlertCircle, CheckCircle2, TrendingUp, TrendingDown, Sparkles, Activity, Radio } from lucide-react
import Link from nextlink
import ReactMarkdown from react-markdown
import remarkGfm from remark-gfm

interface AnalysisItem {
  parameter string
  value string
  status string
  description string
  recommendations string[]
}

interface AnalysisData {
  pros AnalysisItem[]  string
  cons AnalysisItem[]  string
  summary string
  recommendations string
  detailed_analysis {
    xray string
    ctscan string
    mri string
    document string
  }
}

interface AgentStatus {
  status string
  progress number
  message string
}

export default function AIReportReviewPage() {
  const { language } = useLanguage()
  const { isAuthenticated, userEmail } = useAuth()
  const router = useRouter()
  const [uploadedFile, setUploadedFile] = useStateFile  null(null)

  useEffect(() = {
    if (!isAuthenticated) {
      router.push('login')
    }
  }, [isAuthenticated, router])
  
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useStateAnalysisData  null(null)
  const [error, setError] = useStatestring  null(null)
  const [isDragging, setIsDragging] = useState(false)
  const [agentStatuses, setAgentStatuses] = useStateRecordstring, AgentStatus({})
  const [sessionId, setSessionId] = useStatestring()
  const [fileType, setFileType] = useStatestring()
  const [pendingAnalysis, setPendingAnalysis] = useStateAnalysisData  null(null)
  const statusPollIntervalRef = useRefNodeJS.Timeout  null(null)
  const pendingAnalysisRef = useRefAnalysisData  null(null)

  const fileInputRef = useRefHTMLInputElement(null)

   Cleanup polling on unmount
  useEffect(() = {
    return () = {
      if (statusPollIntervalRef.current) {
        clearInterval(statusPollIntervalRef.current)
      }
    }
  }, [])

   Poll for agent status updates
  const startStatusPolling = (sid string) = {
    const pollStatus = async () = {
      try {
        const response = await fetch(`httplocalhost8000apiagent-status${sid}`)
        if (response.ok) {
          const data = await response.json()
          if (data.success && data.agents) {
            setAgentStatuses(data.agents)
            
             Check if all agents are done
            const agentEntries = Object.entries(data.agents)
            const completedOrError = agentEntries.filter(
              ([_, agent] [string, any]) = agent.status === 'completed'  agent.status === 'error'
            )
            const workingAgents = agentEntries.filter(
              ([_, agent] [string, any]) = agent.status === 'working'
            )
            
             Check for stuck agents (working with high progress for too long)
            const stuckAgents = workingAgents.filter(
              ([_, agent] [string, any]) = agent.progress = 0.8
            )
            
            const allDone = agentEntries.length  0 && (
               All agents are completederror
              completedOrError.length === agentEntries.length 
               OR most agents done and any remaining are stuck at high progress (likely hanging)
              (completedOrError.length = agentEntries.length - 1 && stuckAgents.length  0)
            )
            
            if (allDone && agentEntries.length  0) {
              if (statusPollIntervalRef.current) {
                clearInterval(statusPollIntervalRef.current)
                statusPollIntervalRef.current = null
              }
              
                 Mark any stuck agents as completed for display
                if (stuckAgents.length  0) {
                  const updatedStatuses = { ...data.agents }
                  stuckAgents.forEach(([agentName, _] [string, any]) = {
                    updatedStatuses[agentName] = {
                      ...updatedStatuses[agentName],
                      status 'completed',
                      progress 1.0,
                      message 'Analysis complete!'
                    }
                  })
                  setAgentStatuses(updatedStatuses)
                }
                
                 Now that all agents are done, show the analysis results
                const pending = pendingAnalysisRef.current
                if (pending) {
                  setTimeout(() = {
                    setAnalysis(pending)
                    setPendingAnalysis(null)
                    pendingAnalysisRef.current = null
                    setAnalyzing(false)
                  }, 800)  Slightly longer delay to show completion
                } else {
                  setAnalyzing(false)
                }
            }
          }
        }
      } catch (err) {
        console.error(Error polling agent status, err)
      }
    }

     Poll immediately and then every 500ms
    pollStatus()
    statusPollIntervalRef.current = setInterval(pollStatus, 500)
  }

  const stopStatusPolling = () = {
    if (statusPollIntervalRef.current) {
      clearInterval(statusPollIntervalRef.current)
      statusPollIntervalRef.current = null
    }
  }

  const content = {
    en {
      title AI Report Review,
      desc Upload your medical reports and let our AI analyze them for you,
      uploadReport Upload Medical Report,
      dragDrop Drag and drop your report here,
      supportedFormats Supported formats PDF, JPG, PNG, WEBP,
      selectFile Select File,
      analyze Analyze Report,
      analyzing Analyzing...,
      remove Remove,
      analysisResults Analysis Results,
      backHome Back to Home,
    },
  }

  const t = content[language as keyof typeof content]  content.en

  const handleFileSelect = (file File) = {
     Validate file type
    const allowedTypes = ['imagejpeg', 'imagejpg', 'imagepng', 'imagewebp', 'applicationpdf']
    const allowedExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.pdf']
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
    
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
      setError(Please upload a valid file (PDF, JPG, PNG, or WEBP))
      return
    }
    
     Validate file size (max 10MB)
    if (file.size  10  1024  1024) {
      setError(File size too large. Maximum 10MB allowed.)
      return
    }
    
    setUploadedFile(file)
    setError(null)
    setAnalysis(null)
    setAgentStatuses({})
  }

  const handleInputChange = (e React.ChangeEventHTMLInputElement) = {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }

  const handleDragOver = (e React.DragEvent) = {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e React.DragEvent) = {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e React.DragEvent) = {
    e.preventDefault()
    setIsDragging(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleAnalyze = async () = {
    if (!uploadedFile) {
      setError(Please upload a report first)
      return
    }
    
     Generate session_id BEFORE starting analysis
    const newSessionId = `${userEmail  'anon'}_${Date.now()}`
    setSessionId(newSessionId)
    setAgentStatuses({})
    setAnalyzing(true)
    setError(null)
    setAnalysis(null)
    stopStatusPolling()

     Start polling IMMEDIATELY when analysis begins
    startStatusPolling(newSessionId)
    
     Stop polling after 60 seconds max (enough time for analysis)
    setTimeout(() = {
      stopStatusPolling()
    }, 60000)

    try {
      const formData = new FormData()
      formData.append('file', uploadedFile)
      
       Add email if user is authenticated
      if (userEmail) {
        formData.append('email', userEmail)
      }
      
       Send session_id to backend so it can use it
      formData.append('session_id', newSessionId)

      const response = await fetch('httplocalhost8000apianalyze-blood-report', {
        method 'POST',
        body formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail  'Failed to analyze report')
      }

      const data = await response.json()
      
      if (data.success && data.analysis) {
         Store analysis data but DON'T display it yet - wait for all agents to complete
        setFileType(data.file_type  blood_report)
        
         Store the analysis data temporarily to show later (after all agents complete)
        setPendingAnalysis(data.analysis)
        pendingAnalysisRef.current = data.analysis
        
         Keep polling until agents are done (will auto-stop when all complete)
         The polling is already started above
         analyzing state will be set to false automatically when all agents complete
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (err) {
      setError(err instanceof Error  err.message  'An error occurred while analyzing the report. Please make sure the backend is running.')
      stopStatusPolling()
      setAnalyzing(false)
    }
     Note analyzing will be set to false automatically by the polling function when all agents complete
  }

   Parse proscons from string format
  const parseProsCons = (content string  AnalysisItem[]) AnalysisItem[] = {
    if (Array.isArray(content)) {
      return content
    }
    
    if (typeof content !== 'string') {
      return []
    }
    
     Try to parse markdown formatted proscons
    const items AnalysisItem[] = []
    const lines = content.split('n')
    
    let currentItem PartialAnalysisItem  null = null
    
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      
       Check for checkmark (✓) or warning (⚠)
      if (trimmed.startsWith('✓')) {
         Save previous item
        if (currentItem && currentItem.parameter) {
          items.push(currentItem as AnalysisItem)
        }
        
         Start new item
        const match = trimmed.match(✓s(.+)s(.+)s(normal ranges(.+))i)
        if (match) {
          currentItem = {
            parameter match[1].trim(),
            value match[2].trim(),
            status Normal,
            description 
          }
        } else {
           Simple format
          const text = trimmed.substring(1).trim()
          const colonIndex = text.indexOf('')
          if (colonIndex  0) {
            currentItem = {
              parameter text.substring(0, colonIndex).trim(),
              value text.substring(colonIndex + 1).trim(),
              status Normal,
              description 
            }
          }
        }
      } else if (trimmed.startsWith('⚠')) {
         Save previous item
        if (currentItem && currentItem.parameter) {
          items.push(currentItem as AnalysisItem)
        }
        
         Start new warning item
        const match = trimmed.match(⚠s(.+)s(.+)s(normal ranges(.+))i)
        if (match) {
          currentItem = {
            parameter match[1].trim(),
            value match[2].trim(),
            status Abnormal,
            description 
          }
        }
      } else if (currentItem) {
         Add to current item
        if (trimmed.startsWith('Significance')  trimmed.startsWith('Description')) {
          currentItem.description = trimmed.substring(trimmed.indexOf('') + 1).trim()
        } else if (trimmed.startsWith('- ')) {
          if (!currentItem.recommendations) {
            currentItem.recommendations = []
          }
          currentItem.recommendations.push(trimmed.substring(2).trim())
        } else if (!currentItem.description && trimmed.length  0) {
          currentItem.description = trimmed
        }
      }
    }
    
     Add last item
    if (currentItem && currentItem.parameter) {
      items.push(currentItem as AnalysisItem)
    }
    
    return items
  }

  const getAgentDisplayName = (agentName string) string = {
    const names Recordstring, string = {
      'document_processor' 'Document Processor',
      'positive_analyzer' 'Positive Findings Analyzer',
      'negative_analyzer' 'Negative Findings Analyzer',
      'summary_agent' 'Summary Generator',
      'recommendation_agent' 'Recommendation Generator',
      'xray_analyzer' 'X-Ray Analysis',
      'ctscan_analyzer' 'CT Scan Analysis',
      'mri_analyzer' 'MRI Analysis'
    }
    return names[agentName]  agentName.replace('_', ' ').replace(bwg, l = l.toUpperCase())
  }

  const getAgentStatusColor = (status string) string = {
    switch (status) {
      case 'working' return 'text-blue-500'
      case 'completed' return 'text-green-500'
      case 'error' return 'text-red-500'
      case 'idle' return 'text-gray-400'
      default return 'text-gray-500'
    }
  }

  const getAgentStatusIcon = (status string) = {
    switch (status) {
      case 'working' return Loader2 className=w-4 h-4 animate-spin 
      case 'completed' return CheckCircle className=w-4 h-4 
      case 'error' return AlertCircle className=w-4 h-4 
      case 'idle' return Activity className=w-4 h-4 opacity-50 
      default return Activity className=w-4 h-4 
    }
  }

  return (
    div className=min-h-screen flex flex-col bg-background
      Header 

      main className=flex-1 py-12 px-4 mdpx-8
        div className=max-w-6xl mx-auto
          Link href= className=text-primary hovertext-primary80 mb-6 inline-block
            ← {t.backHome}
          Link

          h1 className=text-4xl font-bold text-foreground mb-2{t.title}h1
          p className=text-muted-foreground mb-8{t.desc}p

          { Error Message }
          {error && (
            Card className=mb-8 border-red-300 bg-red-50 darkbg-red-95020
              CardContent className=pt-6
                div className=flex items-center gap-2 text-red-600 darktext-red-400
                  AlertCircle className=w-5 h-5 
                  p{error}p
                div
              CardContent
            Card
          )}

          { Upload Area }
          Card 
            className={`border-2 border-dashed mb-8 transition-colors ${
              isDragging 
                 'border-primary bg-primary5' 
                 'border-border hoverborder-primary50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          
            CardContent className=pt-8
              div className=text-center
                Upload className={`w-16 h-16 text-primary mx-auto mb-4 ${isDragging  'scale-110'  ''} transition-transform`} 
                p className=text-foreground font-semibold mb-2 text-lg{t.dragDrop}p
                p className=text-sm text-muted-foreground mb-6{t.supportedFormats}p
                input
                  ref={fileInputRef}
                  type=file
                  onChange={handleInputChange}
                  className=hidden
                  accept=.pdf,.jpg,.jpeg,.png,.webp,applicationpdf,imagejpeg,imagejpg,imagepng,imagewebp
                
                Button 
                  onClick={() = fileInputRef.current.click()} 
                  className=bg-primary hoverbg-primary90 px-8 py-6 text-lg
                  size=lg
                
                  Upload className=w-5 h-5 mr-2 
                  {t.selectFile}
                Button
              div
            CardContent
          Card

          { File Display }
          {uploadedFile && (
            Card className=mb-8
              CardContent className=pt-6
                div className=flex items-center justify-between p-4 bg-secondary30 rounded-lg border border-primary20
                  div className=flex items-center gap-4
                    div className=p-3 bg-primary10 rounded-lg
                      File className=w-6 h-6 text-primary 
                    div
                    div
                      p className=font-semibold text-foreground text-lg{uploadedFile.name}p
                      p className=text-sm text-muted-foreground{(uploadedFile.size  1024).toFixed(2)} KBp
                    div
                  div
                  button
                    onClick={() = {
                      setUploadedFile(null)
                      setAnalysis(null)
                      setError(null)
                      setAgentStatuses({})
                      stopStatusPolling()
                    }}
                    className=p-2 hoverbg-red-100 darkhoverbg-red-95030 rounded-lg transition-colors
                    title=Remove file
                  
                    X className=w-5 h-5 text-red-500 
                  button
                div
              CardContent
            Card
          )}

          { Agent Status Display }
          {analyzing && (
            Card className=mb-8 border-primary20 bg-gradient-to-br from-primary5 to-primary10
              CardHeader
                CardTitle className=flex items-center gap-2
                  Activity className=w-5 h-5 text-primary 
                  AI Agents Processing
                CardTitle
              CardHeader
              CardContent className=space-y-3
                {Object.keys(agentStatuses).length  0  (
                  Object.entries(agentStatuses).map(([agentName, status]) = (
                    div key={agentName} className=space-y-2
                      div className=flex items-center justify-between
                        div className=flex items-center gap-2
                          {getAgentStatusIcon(status.status)}
                          span className={`font-medium ${getAgentStatusColor(status.status)}`}
                            {getAgentDisplayName(agentName)}
                          span
                        div
                        span className=text-xs text-muted-foreground
                          {Math.round(status.progress  100)}%
                        span
                      div
                      div className=w-full bg-muted rounded-full h-2 overflow-hidden
                        div
                          className={`h-full transition-all duration-300 ${
                            status.status === 'completed'  'bg-green-500' 
                            status.status === 'error'  'bg-red-500' 
                            status.status === 'working'  'bg-blue-500 animate-pulse' 
                            status.status === 'idle'  'bg-gray-300' 
                            'bg-gray-400'
                          }`}
                          style={{ width `${status.progress  100}%` }}
                        
                      div
                      {status.message && (
                        p className=text-xs text-muted-foreground ml-6{status.message}p
                      )}
                    div
                  ))
                )  (
                  div className=flex items-center gap-2 py-4
                    Loader2 className=w-4 h-4 animate-spin text-primary 
                    span className=text-muted-foregroundInitializing agents...span
                  div
                )}
              CardContent
            Card
          )}

          { Analyze Button }
          Button
            onClick={handleAnalyze}
            disabled={analyzing  !uploadedFile}
            className=w-full bg-primary hoverbg-primary90 mb-8 text-lg py-6
            size=lg
          
            {analyzing  (
              
                Loader2 className=w-5 h-5 mr-2 animate-spin 
                {t.analyzing}
              
            )  (
              
                Sparkles className=w-5 h-5 mr-2 
                {t.analyze}
              
            )}
          Button

          { Analysis Results }
          {analysis && (
            div className=space-y-6
              { X-Ray, CT Scan, or MRI Detailed Analysis }
              {(fileType === xray  fileType === ct  fileType === mri) && analysis.detailed_analysis && (
                Card className=border-primary20 bg-gradient-to-br from-primary5 to-primary10
                  CardHeader
                    CardTitle className=flex items-center gap-2
                      Radio className=w-5 h-5 text-primary 
                      {fileType === xray  X-Ray Analysis  fileType === ct  CT Scan Analysis  MRI Analysis}
                    CardTitle
                  CardHeader
                  CardContent
                    div className=prose prose-sm mdprose-base darkprose-invert max-w-none
                      ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h1 ({ node, ...props }) = h1 className=text-2xl font-bold mb-4 mt-6 text-foreground {...props} ,
                          h2 ({ node, ...props }) = h2 className=text-xl font-bold mb-3 mt-5 text-foreground {...props} ,
                          h3 ({ node, ...props }) = h3 className=text-lg font-semibold mb-2 mt-4 text-foreground {...props} ,
                          p ({ node, ...props }) = p className=mb-3 text-foreground leading-relaxed {...props} ,
                          ul ({ node, ...props }) = ul className=list-disc pl-6 mb-4 space-y-1 text-foreground {...props} ,
                          ol ({ node, ...props }) = ol className=list-decimal pl-6 mb-4 space-y-1 text-foreground {...props} ,
                          li ({ node, ...props }) = li className=text-foreground {...props} ,
                          strong ({ node, ...props }) = strong className=font-semibold text-foreground {...props} ,
                        }}
                      
                        {analysis.detailed_analysis.xray  analysis.detailed_analysis.ctscan  analysis.detailed_analysis.mri  analysis.summary  }
                      ReactMarkdown
                    div
                  CardContent
                Card
              )}

              { Summary }
              {analysis.summary && fileType !== xray && fileType !== ct && fileType !== mri && (
                Card className=border-primary20 bg-gradient-to-br from-primary5 to-primary10
                  CardHeader
                    CardTitle className=flex items-center gap-2
                      Sparkles className=w-5 h-5 text-primary 
                      Summary
                    CardTitle
                  CardHeader
                  CardContent
                    div className=prose prose-sm mdprose-base darkprose-invert max-w-none
                      ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h1 ({ node, ...props }) = h1 className=text-2xl font-bold mb-4 mt-6 text-foreground {...props} ,
                          h2 ({ node, ...props }) = h2 className=text-xl font-bold mb-3 mt-5 text-foreground {...props} ,
                          h3 ({ node, ...props }) = h3 className=text-lg font-semibold mb-2 mt-4 text-foreground {...props} ,
                          p ({ node, ...props }) = p className=mb-3 text-foreground leading-relaxed {...props} ,
                          ul ({ node, ...props }) = ul className=list-disc pl-6 mb-4 space-y-1 text-foreground {...props} ,
                          ol ({ node, ...props }) = ol className=list-decimal pl-6 mb-4 space-y-1 text-foreground {...props} ,
                          li ({ node, ...props }) = li className=text-foreground {...props} ,
                          strong ({ node, ...props }) = strong className=font-semibold text-foreground {...props} ,
                        }}
                      
                        {analysis.summary}
                      ReactMarkdown
                    div
                  CardContent
                Card
              )}

              { Pros Section - Normal Values }
              {analysis.pros && (typeof analysis.pros === 'string'  analysis.pros.length  0  analysis.pros.length  0) && (
                Card className=border-green-300 bg-green-5050 darkbg-green-95020
                  CardHeader
                    CardTitle className=flex items-center gap-2 text-green-700 darktext-green-400
                      CheckCircle2 className=w-6 h-6 
                      Normal Values (Pros)
                    CardTitle
                  CardHeader
                  CardContent
                    {typeof analysis.pros === 'string'  (
                      div className=prose prose-sm darkprose-invert max-w-none
                        ReactMarkdown remarkPlugins={[remarkGfm]}
                          {analysis.pros}
                        ReactMarkdown
                      div
                    )  (
                      div className=space-y-4
                        {analysis.pros.map((item, index) = (
                          div
                            key={index}
                            className=p-4 bg-white darkbg-gray-900 rounded-lg border border-green-200 darkborder-green-800 shadow-sm
                          
                            div className=flex items-start justify-between mb-2
                              div className=flex items-center gap-2
                                TrendingUp className=w-5 h-5 text-green-600 darktext-green-400 
                                h3 className=font-bold text-lg text-foreground{item.parameter}h3
                              div
                              span className=px-3 py-1 bg-green-100 darkbg-green-900 text-green-700 darktext-green-300 rounded-full text-sm font-semibold
                                {item.status}
                              span
                            div
                            p className=text-sm text-muted-foreground mb-2
                              span className=font-semibold text-foregroundValue span
                              span className=text-primary font-mono{item.value}span
                            p
                            p className=text-foreground{item.description}p
                          div
                        ))}
                      div
                    )}
                  CardContent
                Card
              )}

              { Cons Section - Abnormal Values with Recommendations }
              {analysis.cons && (typeof analysis.cons === 'string'  analysis.cons.length  0  analysis.cons.length  0) && (
                Card className=border-orange-300 bg-orange-5050 darkbg-orange-95020
                  CardHeader
                    CardTitle className=flex items-center gap-2 text-orange-700 darktext-orange-400
                      AlertCircle className=w-6 h-6 
                      Abnormal Values (Areas of Concern)
                    CardTitle
                  CardHeader
                  CardContent
                    {typeof analysis.cons === 'string'  (
                      div className=prose prose-sm darkprose-invert max-w-none
                        ReactMarkdown remarkPlugins={[remarkGfm]}
                          {analysis.cons}
                        ReactMarkdown
                      div
                    )  (
                      div className=space-y-4
                        {analysis.cons.map((item, index) = (
                          div
                            key={index}
                            className=p-4 bg-white darkbg-gray-900 rounded-lg border border-orange-200 darkborder-orange-800 shadow-sm
                          
                            div className=flex items-start justify-between mb-2
                              div className=flex items-center gap-2
                                TrendingDown className=w-5 h-5 text-orange-600 darktext-orange-400 
                                h3 className=font-bold text-lg text-foreground{item.parameter}h3
                              div
                              span className=px-3 py-1 bg-orange-100 darkbg-orange-900 text-orange-700 darktext-orange-300 rounded-full text-sm font-semibold
                                {item.status}
                              span
                            div
                            p className=text-sm text-muted-foreground mb-2
                              span className=font-semibold text-foregroundValue span
                              span className=text-orange-600 darktext-orange-400 font-mono font-semibold{item.value}span
                            p
                            p className=text-foreground mb-4{item.description}p
                            
                            { Recommendations }
                            {item.recommendations && item.recommendations.length  0 && (
                              div className=mt-4 pt-4 border-t border-orange-200 darkborder-orange-800
                                h4 className=font-semibold text-foreground mb-3 flex items-center gap-2
                                  Sparkles className=w-4 h-4 text-primary 
                                  Recommendations
                                h4
                                ul className=space-y-2
                                  {item.recommendations.map((rec, recIndex) = (
                                    li key={recIndex} className=flex items-start gap-2 text-foreground
                                      CheckCircle className=w-4 h-4 text-primary mt-1 flex-shrink-0 
                                      span{rec}span
                                    li
                                  ))}
                                ul
                              div
                            )}
                          div
                        ))}
                      div
                    )}
                  CardContent
                Card
              )}

              { Recommendations Section }
              {analysis.recommendations && (
                Card className=border-blue-300 bg-blue-5050 darkbg-blue-95020
                  CardHeader
                    CardTitle className=flex items-center gap-2 text-blue-700 darktext-blue-400
                      Sparkles className=w-6 h-6 
                      Recommendations
                    CardTitle
                  CardHeader
                  CardContent
                    div className=prose prose-sm darkprose-invert max-w-none
                      ReactMarkdown remarkPlugins={[remarkGfm]}
                        {analysis.recommendations}
                      ReactMarkdown
                    div
                  CardContent
                Card
              )}

              { Disclaimer }
              Card className=border-blue-200 bg-blue-5050 darkbg-blue-95020
                CardContent className=pt-6
                  div className=flex items-start gap-3
                    AlertCircle className=w-5 h-5 text-blue-600 darktext-blue-400 flex-shrink-0 mt-0.5 
                    p className=text-sm text-foreground
                      span className=font-semiboldImportant span
                      This analysis is AI-generated and should be reviewed by a healthcare professional. 
                      It is not a substitute for professional medical advice, diagnosis, or treatment.
                    p
                  div
                CardContent
              Card
            div
          )}
        div
      main

      Footer 
    div
  )
}