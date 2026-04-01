"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { ArrowUp, Globe, Loader2, Sparkles, Paperclip, Camera, X, FileText, Image as ImageIcon } from "lucide-react"
import Header from "@/components/header"
import { useLanguage } from "@/app/language-context"
import { useAuth } from "@/app/auth-provider"
import { useRouter } from "next/navigation"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface UploadedFile {
  id: string
  file: File
  preview?: string
  type: 'image' | 'pdf' | 'other'
}

export default function ChatbotPage() {
  const { language } = useLanguage()
  const { isAuthenticated, userEmail } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, router])

  const [messages, setMessages] = useState<Array<{ role: string; content: string; files?: UploadedFile[] }>>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [cameraActive, setCameraActive] = useState(false)
  const [sessionId, setSessionId] = useState<string>("")
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const videoInputRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // Generate session ID on mount
  useEffect(() => {
    setSessionId(`${userEmail || 'anon'}_${Date.now()}`)
  }, [userEmail])

  const content = {
    en: {
      title: "Advanced Healthcare Assistant",
      placeholder: "Ask about symptoms, treatments, diet recommendations, or any health concern...",
      send: "Send",
      webSearch: "Use Web Search",
      webSearchTooltip: "Enable to search the internet for current medical information",
      attachFile: "Attach file",
      takePhoto: "Take Photo",
      capture: "Capture",
      cancel: "Cancel",
      remove: "Remove",
    },
    es: {
      title: "Asistente de Salud Avanzado",
      placeholder: "Pregunta sobre síntomas, tratamientos, recomendaciones dietéticas o cualquier preocupación de salud...",
      send: "Enviar",
      webSearch: "Usar Búsqueda Web",
      webSearchTooltip: "Habilitar para buscar en internet información médica actual",
      attachFile: "Adjuntar archivo",
      takePhoto: "Tomar Foto",
      capture: "Capturar",
      cancel: "Cancelar",
      remove: "Eliminar",
    },
  }

  const t = content[language as keyof typeof content] || content.en

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const startCamera = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setError("Camera not available. Please check permissions.")
        return
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" }
      })

      if (videoInputRef.current) {
        videoInputRef.current.srcObject = stream
        await videoInputRef.current.play()
        setCameraActive(true)
      }
    } catch (error) {
      console.error("Camera error:", error)
      setError("Unable to access camera. Please check permissions.")
    }
  }

  const stopCamera = () => {
    if (videoInputRef.current?.srcObject) {
      const tracks = (videoInputRef.current.srcObject as MediaStream).getTracks()
      tracks.forEach(track => track.stop())
      setCameraActive(false)
    }
  }

  const takePhoto = () => {
    if (videoInputRef.current && canvasRef.current) {
      const context = canvasRef.current.getContext("2d")
      if (context && videoInputRef.current.videoWidth > 0) {
        canvasRef.current.width = videoInputRef.current.videoWidth
        canvasRef.current.height = videoInputRef.current.videoHeight
        context.drawImage(videoInputRef.current, 0, 0)
        
        canvasRef.current.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' })
            handleFileSelect(file)
            stopCamera()
          }
        }, 'image/jpeg', 0.9)
      }
    }
  }

  const handleFileSelect = async (file: File) => {
    const fileId = `${Date.now()}_${Math.random()}`
    let preview: string | undefined

    if (file.type.startsWith('image/')) {
      preview = URL.createObjectURL(file)
    }

    const uploadedFile: UploadedFile = {
      id: fileId,
      file,
      preview,
      type: file.type.startsWith('image/') ? 'image' : file.type === 'application/pdf' ? 'pdf' : 'other'
    }

    setUploadedFiles(prev => [...prev, uploadedFile])
  }

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => {
      const file = prev.find(f => f.id === fileId)
      if (file?.preview) {
        URL.revokeObjectURL(file.preview)
      }
      return prev.filter(f => f.id !== fileId)
    })
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      Array.from(e.target.files).forEach(handleFileSelect)
      e.target.value = '' // Reset input
    }
  }

  const handleSendMessage = async () => {
    if ((!input.trim() && uploadedFiles.length === 0) || isLoading) return

    const userMessage = { role: "user", content: input || "Analyze the uploaded file(s)", files: [...uploadedFiles] }
    setMessages((prev) => [...prev, userMessage])
    const currentInput = input
    const currentFiles = [...uploadedFiles]
    setInput("")
    setUploadedFiles([])
    setIsLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('message', currentInput || "Please analyze the uploaded file(s) and provide insights.")
      if (userEmail) {
        formData.append('email', userEmail)
      }
      formData.append('use_web_search', useWebSearch ? "true" : "false")
      if (sessionId) {
        formData.append('session_id', sessionId)
      }

      // Add files
      if (currentFiles.length > 0) {
        currentFiles.forEach(file => {
          formData.append('files', file.file)
        })
      }

      const response = await fetch('http://localhost:8000/api/chatbot', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to get response')
      }

      const data = await response.json()
      
      if (data.success && data.response) {
        const botMessage = {
          role: "assistant",
          content: data.response,
        }
        setMessages((prev) => [...prev, botMessage])
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred. Please make sure the backend is running.')
      console.error("Chatbot error:", err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      <main className="flex-1 flex flex-col h-[calc(100vh-64px)]">
        {/* Camera Modal */}
        {cameraActive && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="flex flex-col gap-4 items-center bg-card p-6 rounded-xl">
              <video 
                ref={videoInputRef} 
                autoPlay 
                playsInline 
                className="w-full max-w-md h-auto rounded-lg bg-black" 
              />
              <canvas ref={canvasRef} className="hidden" />
              <div className="flex gap-4">
                <button
                  onClick={takePhoto}
                  className="bg-primary text-primary-foreground px-6 py-2 rounded-full font-semibold hover:bg-primary/90"
                >
                  <Camera className="w-5 h-5 inline mr-2" />
                  {t.capture}
                </button>
                <button
                  onClick={stopCamera}
                  className="bg-destructive text-destructive-foreground px-6 py-2 rounded-full font-semibold hover:bg-destructive/90"
                >
                  {t.cancel}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Main Chat Area - Full Width */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 lg:px-12 xl:px-16 py-6">
          {messages.length === 0 ? (
            <div className="max-w-4xl mx-auto text-center py-12">
              <div className="mb-6">
                <Sparkles className="w-16 h-16 text-primary mx-auto mb-4" />
              </div>
              <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">{t.title}</h1>
              <p className="text-lg text-muted-foreground mb-8">
                Get personalized health advice, treatment plans, diet recommendations, and more.
                {userEmail && " Your medical history will be considered for personalized responses."}
              </p>
            </div>
          ) : (
            <div className="max-w-5xl mx-auto flex flex-col space-y-6">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] md:max-w-[75%] lg:max-w-[70%] rounded-2xl px-6 py-4 ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground rounded-br-sm"
                        : "bg-secondary text-foreground rounded-bl-sm border border-border/50"
                    }`}
                  >
                    {/* Show uploaded files in user messages */}
                    {msg.files && msg.files.length > 0 && (
                      <div className="mb-3 space-y-2">
                        {msg.files.map((file) => (
                          <div key={file.id} className="relative">
                            {file.type === 'image' && file.preview ? (
                              <img 
                                src={file.preview} 
                                alt={file.file.name}
                                className="max-w-full max-h-64 rounded-lg object-contain"
                              />
                            ) : (
                              <div className="flex items-center gap-2 bg-muted/30 p-3 rounded-lg">
                                <FileText className="w-5 h-5" />
                                <span className="text-sm">{file.file.name}</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {msg.role === "assistant" ? (
                      <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h1: ({ node, ...props }) => <h1 className="text-2xl font-bold mb-4 mt-6 text-foreground" {...props} />,
                            h2: ({ node, ...props }) => <h2 className="text-xl font-bold mb-3 mt-5 text-foreground" {...props} />,
                            h3: ({ node, ...props }) => <h3 className="text-lg font-semibold mb-2 mt-4 text-foreground" {...props} />,
                            p: ({ node, ...props }) => <p className="mb-3 text-foreground leading-relaxed" {...props} />,
                            ul: ({ node, ...props }) => <ul className="list-disc pl-6 mb-4 space-y-1 text-foreground" {...props} />,
                            ol: ({ node, ...props }) => <ol className="list-decimal pl-6 mb-4 space-y-1 text-foreground" {...props} />,
                            li: ({ node, ...props }) => <li className="text-foreground" {...props} />,
                            strong: ({ node, ...props }) => <strong className="font-semibold text-foreground" {...props} />,
                            em: ({ node, ...props }) => <em className="italic text-foreground" {...props} />,
                            code: ({ node, inline, ...props }: any) =>
                              inline ? (
                                <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground" {...props} />
                              ) : (
                                <code className="block bg-muted p-3 rounded-md text-sm font-mono overflow-x-auto text-foreground" {...props} />
                              ),
                            hr: ({ node, ...props }) => <hr className="my-4 border-border" {...props} />,
                            blockquote: ({ node, ...props }) => (
                              <blockquote className="border-l-4 border-primary pl-4 italic my-4 text-muted-foreground" {...props} />
                            ),
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-primary-foreground whitespace-pre-wrap">{msg.content}</p>
                    )}
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-secondary text-secondary-foreground px-6 py-4 rounded-2xl rounded-bl-sm border border-border/50">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-foreground rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-foreground rounded-full animate-bounce [animation-delay:0.2s]" />
                      <div className="w-2 h-2 bg-foreground rounded-full animate-bounce [animation-delay:0.4s]" />
                    </div>
                  </div>
                </div>
              )}
              
              {error && (
                <div className="flex justify-start">
                  <div className="bg-destructive/10 text-destructive px-6 py-4 rounded-2xl rounded-bl-sm border border-destructive/20">
                    <p className="text-sm">{error}</p>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area - Full Width */}
        <div className="bg-card/80 backdrop-blur-sm border-t border-border px-4 md:px-8 lg:px-12 xl:px-16 py-4">
          <div className="max-w-5xl mx-auto">
            {/* Web Search Toggle */}
            <div className="flex items-center justify-end mb-3">
              <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                <input
                  type="checkbox"
                  checked={useWebSearch}
                  onChange={(e) => setUseWebSearch(e.target.checked)}
                  className="w-4 h-4 rounded border-border"
                />
                <Globe className="w-4 h-4" />
                <span>{t.webSearch}</span>
              </label>
            </div>

            {/* File Preview - ChatGPT Style */}
            {uploadedFiles.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {uploadedFiles.map((file) => (
                  <div key={file.id} className="relative group">
                    {file.type === 'image' && file.preview ? (
                      <div className="relative">
                        <img 
                          src={file.preview} 
                          alt={file.file.name}
                          className="w-20 h-20 object-cover rounded-lg border border-border"
                        />
                        <button
                          onClick={() => removeFile(file.id)}
                          className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ) : (
                      <div className="relative flex items-center gap-2 bg-muted p-2 rounded-lg border border-border">
                        <FileText className="w-4 h-4" />
                        <span className="text-xs max-w-[120px] truncate">{file.file.name}</span>
                        <button
                          onClick={() => removeFile(file.id)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Input Bar */}
            <div className="flex gap-2 items-center bg-muted/50 rounded-xl px-3 py-2 border border-border/50 focus-within:border-primary/50 transition-colors">
              {/* File Upload Button with Menu */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors p-1.5 rounded-full hover:bg-muted"
                  title={t.attachFile}
                >
                  <Paperclip size={18} />
                </button>
                
                {/* Hidden file inputs */}
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileInputChange}
                  accept="image/*,.pdf"
                  className="hidden"
                />
                <input
                  ref={imageInputRef}
                  type="file"
                  multiple
                  onChange={(e) => {
                    if (e.target.files) {
                      Array.from(e.target.files).forEach(handleFileSelect)
                      e.target.value = ''
                    }
                  }}
                  accept="image/*"
                  className="hidden"
                />
              </div>

              {/* Camera Button */}
              <button
                type="button"
                onClick={startCamera}
                className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors p-1.5 rounded-full hover:bg-muted"
                title={t.takePhoto}
              >
                <Camera size={18} />
              </button>
              
              <textarea
                placeholder={t.placeholder}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage()
                  }
                }}
                rows={1}
                className="flex-1 bg-transparent text-foreground placeholder-muted-foreground outline-none resize-none text-sm leading-5 py-1.5 max-h-24 overflow-y-auto"
                style={{ minHeight: '20px', height: 'auto' }}
              />
              
              <button
                onClick={handleSendMessage}
                disabled={(!input.trim() && uploadedFiles.length === 0) || isLoading}
                className="text-primary-foreground bg-primary rounded-full p-1.5 hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                title={t.send}
              >
                {isLoading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <ArrowUp size={16} />
                )}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}