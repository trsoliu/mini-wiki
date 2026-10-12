# 专利地图

解读笔记攒多了不好翻？点名后在本机摊开五种图。只读库，**不改技能、不改笔记**。
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
<tr><td nowrap width="1%"><strong>五种图</strong></td><td>地形看技术扎堆在哪，四象限看申请人站位，引证网看同族怎么串，功效矩阵看手段对功效，仪表盘看这一库的家底</td></tr>
<tr><td nowrap width="1%"><strong>本机页面</strong></td><td>说一声就起本机页，浏览器打开即可。图上的点来自已读解读笔记；加速副本在 <code>{Documents}/patent-disclosure-skill/patent-map/</code>（和 oa 同级，<code>PATENT_MAP_HOME</code> 可改）</td></tr>
<tr><td nowrap width="1%"><strong>地形怎么摊</strong></td><td>按中文小模型把案例铺到沙盘上（<code>bge-small-zh</code>，本机 ONNX，不用 PyTorch）。模型也落在上面那个目录；没装也能开图，地形先按分类号簇</td></tr>
</tbody>
</table>

用法：「专利地图」或「案例地图」。库里要先有通俗解读笔记；本包不读专利全文。
