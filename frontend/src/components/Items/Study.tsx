import { useEffect, useState } from "react"
import { z } from "zod"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select"

import { ItemsService } from "../../client/sdk.gen"

// 使用zod来约束value的类型
const formSchema = z.object({
    value: z.string(),

})

const propsSchema = z.object({
    value_data: z.object({
        name: z.string(),
        age: z.number(),
    }).optional()
})

// infer是zod的类型推断工具，可以推断出value的类型
type FormData = z.infer<typeof formSchema>
type PropsData = z.infer<typeof propsSchema>

const Study = (data: PropsData) => {
    const [value, setValue] = useState<FormData>({
        value: "你好哇",
    })
    useEffect(() => {
        getInfo()
    }, [])

    const getInfo = async () => {
        const res = await ItemsService.getOrderInfo({ order_id: "1" })
        console.log(res)
    }

    return (
        <div>
            <Select value={value.value} onValueChange={(value) => setValue({ value })}>
                <SelectTrigger>
                    <SelectValue placeholder="Select a value" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="value1">Value 1</SelectItem>
                    <SelectItem value="value2">Value 2</SelectItem>
                    <SelectItem value="value3">Value 3</SelectItem>
                </SelectContent>
            </Select>
        </div>
    )
}

export default Study