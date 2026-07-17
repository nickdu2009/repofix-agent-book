# 在线语法练习

本页只用于小型、无密钥的语法练习。Python 代码由浏览器下载固定版本的 Pyodide 后在 Web Worker 中执行；页面不会读取仓库、Cookie、Local Storage 或任何 OpenAI/Daytona 凭据，也不会调用模型。

!!! warning "在线练习不是不可信代码安全沙箱"
    只运行你理解的短代码。运行器会限制源码长度并在 30 秒后终止 Worker，但它不能替代 RepoFix 的 Daytona 隔离、资源限额或项目测试。

## Python 3.14 小练习

下面的运行时固定为 Pyodide 314.0.2。修改函数，让两个断言都通过；不需要安装包或填写 API Key。

<section class="repofix-python-runner" aria-labelledby="python-runner-title">
  <h3 id="python-runner-title">上下文预算练习</h3>
  <label for="python-runner-code">Python 源码</label>
  <textarea id="python-runner-code" data-runner-code spellcheck="false">def within_budget(costs: list[int], budget: int) -> bool:
    return sum(costs) <= budget

assert within_budget([2, 3], 5)
assert not within_budget([4, 3], 5)
print("checks passed")</textarea>
  <div class="repofix-runner-actions">
    <button type="button" data-runner-run>在浏览器中运行</button>
    <span data-runner-status aria-live="polite">尚未加载 Python 运行时</span>
  </div>
  <pre data-runner-output aria-live="polite">输出会显示在这里。</pre>
</section>

首次运行需要联网下载 Pyodide；运行器不会自动安装代码中导入的第三方包。Pyodide 的加载方式和浏览器支持可参考其[官方使用文档](https://pyodide.org/en/stable/usage/index.html)。

## Go 与 TypeScript

本书不代理或嵌入远程编译 API。需要纯浏览器语法实验时，直接使用语言维护方提供的页面：

- [Go Playground](https://go.dev/play/)：适合单文件、标准库范围的小程序；
- [TypeScript Playground](https://www.typescriptlang.org/play/)：适合联合类型、类型收窄和 Reducer 练习。

在线 Playground 不含 RepoFix 仓库上下文，也不应粘贴 Secret、私有源码或模型输出中的未知命令。

## 章节实验的真实验收

`chapter-check` 是安全的结构检查：它只检查完成标记、产物类型和遗留占位符，**不会执行学习者代码**。实践章还应运行相应语言的行为验证：

```bash
cd examples/repofix

# Python 章节：03、04、05、06、09、13、14
python .work/chapter-03/exercise.py

# Go 章节：10
go run .work/chapter-10/main.go

# TypeScript 章节：15、16（Node.js 24 可直接剥离可擦除类型）
apps/web/node_modules/.bin/tsc --noEmit --strict --target ES2024 \
  --moduleDetection force .work/chapter-15/exercise.ts
node .work/chapter-15/exercise.ts

# 结构验收始终单独执行
python scripts/chapter_lab.py check chapter-03
```

完整项目的单元测试、契约测试和 Fake E2E 仍在 Codespaces 或本地环境运行；页面内练习不能替代它们。
