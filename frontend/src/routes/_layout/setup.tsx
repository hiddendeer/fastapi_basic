import { createFileRoute } from "@tanstack/react-router"
import { ProjectTable } from "@/pages/setup-index"

export const Route = createFileRoute("/_layout/setup")({
    component: SetupPage,
    head: () => ({
        meta: [
            {
                title: "项目设置 - FastAPI Cloud",
            },
        ],
    }),
})

function SetupPage() {
    return (
        <div className="flex flex-col gap-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">项目列表</h1>
                <p className="text-muted-foreground">在这里管理和查看您的所有项目</p>
            </div>
            {/* 渲染你刚才创建的组件 */}
            <ProjectTable />
        </div>
    )
}