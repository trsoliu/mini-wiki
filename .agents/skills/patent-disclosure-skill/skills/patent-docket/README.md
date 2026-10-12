# 专利案卷（交底到申请）

工程师把材料丢进来，就按顺序写出交底书和申请文件；清单上的问题最多来回三轮。缺事实问人，不编。
<!-- 使用 HTML 表格：避免 GitHub 管道表把左列挤窄 -->
<table>
<colgroup>
<col width="1%">
<col>
</colgroup>
<thead>
<tr><th align="left" nowrap width="1%">能力</th><th align="left">说明</th></tr>
</thead>
<tbody>
<tr><td nowrap width="1%"><strong>一趟写完</strong></td><td>还没有交底也能开写：先出交底书，再出申请文件四件套，少让工程师和代理人反复对稿</td></tr>
<tr><td nowrap width="1%"><strong>清单再改</strong></td><td>读申请文件 <code>问题清单.md</code>：真问题才改；该改交底、该只改申请、或必须问人，分清楚</td></tr>
<tr><td nowrap width="1%"><strong>最多三轮</strong></td><td>同一案最多来回 3 轮；第 3 轮结束就停，清单没清完也停</td></tr>
<tr><td nowrap width="1%"><strong>不编事实</strong></td><td>只根据已有材料成文；材料没有的标出来问人，不把聊天记忆当成技术事实</td></tr>
<tr><td nowrap width="1%"><strong>案卷落盘</strong></td><td>进度在 <code>outputs/docket/{案件}/docket.yaml</code> 与 <code>TRACKER.md</code></td></tr>
</tbody>
</table>

用法：「交底和申请一起做」；「从零出交底和申请」；「按这份问题清单改」；「继续上次案卷」。产物 → `outputs/docket/`。
