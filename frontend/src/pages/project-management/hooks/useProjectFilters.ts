import { useState, useMemo } from "react"
import type { Project } from "../types"

export const useProjectFilters = (projects: Project[] | undefined) => {
    const [search, setSearch] = useState("")
    const [statusFilter, setStatusFilter] = useState<Project["status"] | "all">("all")

    const filteredProjects = useMemo(() => {
        if (!projects) return []
        return projects.filter((p) => {
            const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase())
            const matchesStatus = statusFilter === "all" || p.status === statusFilter
            return matchesSearch && matchesStatus
        })
    }, [projects, search, statusFilter])

    return {
        search,
        setSearch,
        statusFilter,
        setStatusFilter,
        filteredProjects,
    }
}
