import { useProjects } from "../api/projects"
import { useProjectFilters } from "../hooks/useProjectFilters"
import { Input } from "@/components/ui/input"
import { VuetoReact, ProjectContext } from "./VuetoReact"

export const ProjectTable = () => {
    const { data: projects, isLoading } = useProjects()
    const { search, setSearch, filteredProjects } = useProjectFilters(projects)

    if (isLoading) return <div>Loading projects...</div>

    const onyes = (total: number) => {
        console.log("yes", total)
    }

    return (
        <div className="space-y-4">
            <ProjectContext.Provider value={{ name: "张三", onYes: onyes }}>
                <VuetoReact name="张三" onYes={onyes}>
                    <div className="bg-blue-50 text-blue-600 p-2 rounded text-sm">
                        🚀 这是一个插入到子组件的 React Slot (Children) 示例
                    </div>
                </VuetoReact>
            </ProjectContext.Provider>

            <div className="flex items-center gap-2">
                <Input
                    type="text"
                    placeholder="搜索项目..."
                    className="border rounded px-3 py-2 w-full max-w-sm"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            <div className="rounded-md border">
                <table className="min-w-full divide-y divide-border">
                    <thead className="bg-muted/50">
                        <tr>
                            <th className="px-4 py-3 text-left text-sm font-medium">项目名称</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">状态</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">创建时间</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border bg-background">
                        {filteredProjects.map((project) => (
                            <tr key={project.id} className="hover:bg-muted/50 transition-colors">
                                <td className="px-4 py-3 text-sm">{project.name}</td>
                                <td className="px-4 py-3 text-sm">
                                    <span className={`px-2 py-1 rounded-full text-xs ${project.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-700"
                                        }`}>
                                        {project.status}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-sm text-muted-foreground">
                                    {new Date(project.created_at).toLocaleDateString()}
                                </td>
                            </tr>
                        ))}
                        {filteredProjects.length === 0 && (
                            <tr>
                                <td colSpan={3} className="px-4 py-8 text-center text-muted-foreground">
                                    暂无项目数据
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
