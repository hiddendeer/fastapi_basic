export interface Project {
    id: string
    name: string
    description: string
    status: "active" | "archived" | "on-hold"
    created_at: string
}

export interface CreateProject {
    name: string
    description?: string
}

export interface UpdateProject extends Partial<CreateProject> {
    status?: Project["status"]
}
