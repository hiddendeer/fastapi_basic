import { useState, useRef, useEffect } from "react"
import { Send, Languages, Sparkles, User, Bot, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { OpenAPI } from "@/client/core/OpenAPI"

interface Message {
    role: "user" | "assistant"
    content: string
    language?: string
}

export const ProjectTable = () => {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState("")
    const [targetLang, setTargetLang] = useState("中文")
    const [isStreaming, setIsStreaming] = useState(false)
    const scrollRef = useRef<HTMLDivElement>(null)

    // 自动滚动到最新消息
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [messages])

    const handleTranslate = async () => {
        if (!input.trim() || isStreaming) return

        const userText = input.trim()
        setInput("")

        // 添加用户消息
        const userMsg: Message = { role: "user", content: userText }
        setMessages(prev => [...prev, userMsg])

        // 准备开始流式接收
        setIsStreaming(true)
        const assistantMsg: Message = { role: "assistant", content: "", language: targetLang }
        setMessages(prev => [...prev, assistantMsg])

        try {
            // 获取 Token
            const token = typeof OpenAPI.TOKEN === 'function' ? await OpenAPI.TOKEN() : OpenAPI.TOKEN;

            const response = await fetch(`${OpenAPI.BASE}/api/v1/ai-agents/translate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    text: userText,
                    target_language: targetLang,
                }),
            })

            if (!response.ok) throw new Error("翻译请求失败")

            const reader = response.body?.getReader()
            if (!reader) throw new Error("无法读取响应流")

            const decoder = new TextDecoder()
            let accumulatedContent = ""

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const chunk = decoder.decode(value, { stream: true })
                accumulatedContent += chunk

                // 更新最后一条消息内容
                setMessages(prev => {
                    const next = [...prev]
                    if (next.length > 0) {
                        next[next.length - 1] = {
                            ...next[next.length - 1],
                            content: accumulatedContent
                        }
                    }
                    return next
                })
            }
        } catch (error) {
            console.error("Streaming error:", error)
            setMessages(prev => {
                const next = [...prev]
                if (next.length > 0) {
                    next[next.length - 1] = {
                        ...next[next.length - 1],
                        content: "出错了，请稍后再试。"
                    }
                }
                return next
            })
        } finally {
            setIsStreaming(false)
        }
    }

    const clearHistory = () => {
        setMessages([])
    }

    return (
        <Card className="w-full max-w-4xl mx-auto shadow-xl border-t-4 border-t-primary/20 bg-background/50 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 border-b">
                <div className="flex flex-col">
                    <CardTitle className="flex items-center gap-2 text-xl font-bold">
                        <Sparkles className="w-5 h-5 text-primary animate-pulse" />
                        AI 智能翻译
                    </CardTitle>
                    <CardDescription>使用 LangChain 驱动的流式链式调用</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                    <Select value={targetLang} onValueChange={setTargetLang}>
                        <SelectTrigger className="w-[120px] h-9">
                            <Languages className="w-4 h-4 mr-2" />
                            <SelectValue placeholder="目标语言" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="中文">中文</SelectItem>
                            <SelectItem value="English">English</SelectItem>
                            <SelectItem value="日本語">日本語</SelectItem>
                            <SelectItem value="Français">Français</SelectItem>
                            <SelectItem value="Deutsch">Deutsch</SelectItem>
                        </SelectContent>
                    </Select>
                    <Button variant="ghost" size="icon" onClick={clearHistory} title="清除历史">
                        <Trash2 className="w-4 h-4 text-muted-foreground" />
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                {/* 消息展示区域 */}
                <div
                    ref={scrollRef}
                    className="h-[500px] overflow-y-auto p-6 space-y-6 scroll-smooth"
                >
                    {messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-muted-foreground space-y-4">
                            <div className="p-4 bg-muted rounded-full">
                                <Languages className="w-8 h-8 opacity-50" />
                            </div>
                            <p className="text-sm">在下方输入文字，即可体验 AI 流式翻译</p>
                        </div>
                    ) : (
                        messages.map((msg, idx) => (
                            <div
                                key={idx}
                                className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                            >
                                <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                                    }`}>
                                    {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
                                </div>
                                <div className={`flex flex-col max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                                    {msg.role === "assistant" && (
                                        <div className="flex items-center gap-2 mb-1 px-1">
                                            <Badge variant="outline" className="text-[10px] py-0 h-4">
                                                {msg.language}
                                            </Badge>
                                        </div>
                                    )}
                                    <div className={`p-3 rounded-2xl shadow-sm text-sm leading-relaxed ${msg.role === "user"
                                            ? "bg-primary text-primary-foreground rounded-tr-none"
                                            : "bg-muted/80 backdrop-blur-sm rounded-tl-none border border-border"
                                        }`}>
                                        {msg.content || (isStreaming && idx === messages.length - 1 ? (
                                            <span className="flex gap-1 items-center">
                                                <span className="h-1.5 w-1.5 bg-foreground/50 rounded-full animate-bounce" />
                                                <span className="h-1.5 w-1.5 bg-foreground/50 rounded-full animate-bounce [animation-delay:0.2s]" />
                                                <span className="h-1.5 w-1.5 bg-foreground/50 rounded-full animate-bounce [animation-delay:0.4s]" />
                                            </span>
                                        ) : "...")}
                                        {msg.role === "assistant" && isStreaming && idx === messages.length - 1 && (
                                            <span className="inline-block w-1.5 h-4 ml-1 bg-primary animate-pulse align-middle" />
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* 输入区域 */}
                <div className="p-4 border-t bg-muted/30">
                    <form
                        onSubmit={(e) => { e.preventDefault(); handleTranslate(); }}
                        className="flex gap-2"
                    >
                        <Input
                            placeholder="输入要翻译的文本..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            disabled={isStreaming}
                            className="flex-1 bg-background shadow-inner h-11"
                        />
                        <Button
                            type="submit"
                            disabled={isStreaming || !input.trim()}
                            className="bg-primary hover:bg-primary/90 shadow-md h-11 px-6"
                        >
                            {isStreaming ? (
                                <Sparkles className="w-5 h-5 animate-spin" />
                            ) : (
                                <Send className="w-5 h-5" />
                            )}
                        </Button>
                    </form>
                    <p className="text-[10px] text-center text-muted-foreground mt-2">
                        基于 LangChain LCEL 构建的流式输出管道
                    </p>
                </div>
            </CardContent>
        </Card>
    )
}
