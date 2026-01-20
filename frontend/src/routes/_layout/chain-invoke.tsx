import { createFileRoute } from "@tanstack/react-router"
import { ProjectTable } from "@/pages/chain-invoke"

export const Route = createFileRoute("/_layout/chain-invoke")({
    component: ChainInvokePage,
    head: () => ({
        meta: [
            {
                title: "链式调用 - FastAPI Cloud",
            },
        ],
    }),
})

function ChainInvokePage() {
    return (
        <div className="flex flex-col gap-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">链式调用</h1>
                <p className="text-muted-foreground">在这里管理和执行您的 AI 链式调用</p>
            </div>
            <ProjectTable />
        </div>
    )
}
