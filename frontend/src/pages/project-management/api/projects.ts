import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
// import { ProjectsService } from "@/client" // 假设以后生成的 client 包含这个
import type { Project, CreateProject } from "../types"

// 模拟 API 调用逻辑，方便演示
const mockProjects: Project[] = [
    { id: "1", name: "企业官网建设", description: "项目描述...", status: "active", created_at: new Date().toISOString() },
]

export const projectKeys = {
    all: ["projects"] as const,
    lists: () => [...projectKeys.all, "list"] as const,
    details: () => [...projectKeys.all, "detail"] as const,
    detail: (id: string) => [...projectKeys.details(), id] as const,
}

export const useProjects = () => {
    return useQuery({
        queryKey: projectKeys.lists(),
        queryFn: async () => {
            // 实际开发时换成: return ProjectsService.readProjects()
            return mockProjects
        },
    })
}

export const useCreateProject = () => {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (data: CreateProject) => {
            // 实际开发时换成: return ProjectsService.createProject({ requestBody: data })
            console.log("Creating project:", data)
            return { id: Math.random().toString(), ...data }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
        },
    })
}
