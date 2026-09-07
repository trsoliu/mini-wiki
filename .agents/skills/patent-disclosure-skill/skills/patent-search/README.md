# 专利著录检索

按发明人、申请人、分类号或名称检索公布公告，输出检索报告。
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
<tr><td nowrap width="1%"><strong>检索字段</strong></td><td>走国知局公布站高级查询：发明人、申请人、分类号、名称</td></tr>
<tr><td nowrap width="1%"><strong>检索报告</strong></td><td>结果落到 <code>outputs/patent-search/SEARCH-*.md</code></td></tr>
<tr><td nowrap width="1%"><strong>翻页</strong></td><td>默认先翻前面几页；对话里说「多翻几页」或「全部翻完」再加码；没翻完时不会当成完整清单</td></tr>
<tr><td nowrap width="1%"><strong>个人清单</strong></td><td>带上「发明人姓名 + 当前及历史申请主体」，例如「检索某发明人在申请主体一、申请主体二名下的公开专利」；只覆盖已公开/公告记录，不等于单位内部实际提交总数</td></tr>
</tbody>
</table>

用法：「按发明人/申请人检索公开专利」。无需本地样例，联网出清单 → `outputs/patent-search/SEARCH-*.md`。
