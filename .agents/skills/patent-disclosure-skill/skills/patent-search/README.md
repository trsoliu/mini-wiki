# 专利著录检索

按发明人、申请人、分类号、名称或摘要检索公布公告；也可从单图或权利要求生成检索式，输出检索报告。
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
<tr><td nowrap width="1%"><strong>检索字段</strong></td><td>走国知局公布站高级查询：发明人、申请人、分类号、名称、摘要/简要说明</td></tr>
<tr><td nowrap width="1%"><strong>单图 / 权要</strong></td><td>读一张图或一段权利要求，抽出名称与摘要关键字（可加分类号），再走同一公布站查询。单图必须指定或看图推断专利类型（禁止四类全选）；外观与实用新型用不同抽词口径。不是以图搜图，也不是权要语义检索</td></tr>
<tr><td nowrap width="1%"><strong>检索报告</strong></td><td>结果落到 <code>outputs/patent-search/SEARCH-*.md</code>；派生检索会写入免责声明。按特征精排另出 <code>SEARCH-*.covers.md</code>，不覆盖列表</td></tr>
<tr><td nowrap width="1%"><strong>翻页</strong></td><td>默认先翻前面几页；对话里说「多翻几页」或「全部翻完」再加码；没翻完时不会当成完整清单</td></tr>
<tr><td nowrap width="1%"><strong>个人清单</strong></td><td>带上「发明人姓名 + 当前及历史申请主体」，例如「检索某发明人在申请主体一、申请主体二名下的公开专利」；只覆盖已公开/公告记录，不等于单位内部实际提交总数</td></tr>
</tbody>
</table>

用法：「按发明人/申请人检索公开专利」；「用这张产品图查类似外观」；「按这段权要查相关专利」。无需本地样例，联网出清单 → `outputs/patent-search/SEARCH-*.md`。
