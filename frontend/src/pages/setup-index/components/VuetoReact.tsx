import { useState, useMemo, useEffect, ReactNode } from "react"
import { createContext, useContext } from "react"
export const ProjectContext = createContext({ name: "", onYes: (total: any) => { } })
const infoMap = [
    {
        name: "张三",
        age: 18,
        sex: "男"
    },
    {
        name: "李四",
        age: 19,
        sex: "女"
    },
    {
        name: "王五",
        age: 20,
        sex: "男"
    }
]

export const VuetoReact = ({ name, onYes, children }: { name: string, onYes: (total: number) => void, children?: ReactNode }) => {

    const [count, setCount] = useState(0)
    const context = useContext(ProjectContext)
    console.log(context.name)

    const total = useMemo(() => {
        return count * 2
    }, [count])
    useEffect(() => {
        console.log(name)
    }, [name])

    const changeClick = () => {
        setCount(count + 1)
        onYes(total)
    }

    return (
        <div>
            <h1>VuetoReact</h1>
            {/* Slot 插槽演示区域 */}
            <div className="border border-dashed border-gray-300 p-4 my-2 rounded bg-gray-50/50">
                <p className="text-xs text-gray-500 mb-2">Slot (Children) 区域:</p>
                {children}
            </div>
            <p>Count: {count}</p>
            <p>Total: {total}</p>
            <button onClick={changeClick}>Increment</button>
            {
                infoMap.map((item) => (
                    item.name == '张三' ?
                        <div key={item.name}>
                            <p>Name: {item.name}</p>
                            <p>Age: {item.age}</p>
                            <p>Sex: {item.sex}</p>
                        </div> : null
                ))
            }
        </div>
    )
}