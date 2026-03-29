# 模块准备
import pandas as pd
import numpy as np
import warnings 
import plotly as py
import plotly.graph_objs as go
import plotly.express as px
from flask import Flask, render_template
warnings.filterwarnings('ignore')


app = Flask(__name__)


# 读取数据
def read_data():
    return pd.read_csv('job.csv',header=None,names=['职位','城市','公司','薪资','学历','工作经验','行业标签'])

df = read_data()


# 数据清洗
df.drop_duplicates(keep='first',inplace=True)  #去除重复值

# 考虑到数据中有实习岗位，实习岗薪资按天算，不具有太大的参考价值，故删除包含实习的数据
shixi=df['职位'].str.contains('实习')
df=df[~shixi]
df.reset_index(drop=True,inplace=True)

#城市列包含的值太杂，且本项目分析不需要用到详细地址。鉴于城市数据不规范，所以进行处理，全部转换为城市名
df['城市']=df['城市'].str[:2]

# 将薪资列的值进行拆分，新增最低薪资，最高薪资两列，作为一个岗位薪资的最低值和最高值
df['最低薪资']=df['薪资'].str.extract('^(\d+).*')
df['最高薪资']=df['薪资'].str.extract('^.*?-(\d+).*')

# 有些公司的薪资是单个值，则用最低薪资列的值填充最高薪资列。
df['最高薪资'].fillna(df['最低薪资'],inplace=True)

# 奖金率
df['奖金率']=df['薪资'].str.extract('^.*?·(\d{2})薪')
df['奖金率'].fillna(12,inplace=True)
df['奖金率']=df['奖金率'].astype('float64')
df['奖金率']=df['奖金率']/12

# 将最低薪资，最高薪资，奖金率列转换为数值形式，并以此计算出每个岗位的平均薪资作为新增列
df['最低薪资'] = df['最低薪资'].astype('int64')
df['最高薪资'] = df['最高薪资'].astype('int64')
df['平均薪资'] = (df['最低薪资']+df['最高薪资'])/2*df['奖金率']
df['平均薪资'] = df['平均薪资'].astype('int64')

#调整顺序
cols=list(df)
cols.insert(4,cols.pop(cols.index('最低薪资')))
cols.insert(5,cols.pop(cols.index('最高薪资')))
cols.insert(6,cols.pop(cols.index('奖金率')))
cols.insert(7,cols.pop(cols.index('平均薪资')))
df=df.loc[:,cols]

# 发现极端值，数量都很少，剔除月薪小于2000大于55000的数据
df=df[(df.平均薪资>2)&(df.平均薪资<55)]

# 清洗工作经验数据
df['工作经验'].replace('5-10年学历','5-10年',inplace=True)
df['工作经验'].replace('3-5年学历','3-5年',inplace=True)
df['工作经验'].replace('经验不限学历','经验不限',inplace=True)
df['工作经验'].replace('1-3年学历','1-3年',inplace=True)
df['工作经验'].replace('1年以内学历','1年以内',inplace=True)
df['工作经验'].replace('经验不限中专/','经验不限',inplace=True)
df['工作经验'].replace('1年以内中专/','1年以内',inplace=True)
df['工作经验'].replace('1-3年中专/','1-3年',inplace=True)

#清洗行业标签
df.loc[~df['行业标签'].isin(['互联网','计算机软件','移动互联网','电子商务','数据服务',
                           '互联网金融','游戏','在线教育','生活服务','O2O','医疗健康','贸易/进出口','企业服务','银行']),'行业标签']='其他行业'

new_df = df


# 综合仪表盘页面（默认页面）
@app.route('/', methods=['GET'])
@app.route('/dashboard', methods=['GET'])
def dashboard() -> 'html':
    # 生成不同城市的平均薪资图表
    city=list(new_df.平均薪资.groupby(new_df['城市']).agg(['mean','median']).reset_index().iloc[:,0])
    mean=list(new_df.平均薪资.groupby(new_df['城市']).agg(['mean','median']).reset_index().iloc[:,1])
    median=list(new_df.平均薪资.groupby(new_df['城市']).agg(['mean','median']).reset_index().iloc[:,2])
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
    x=city, 
    y=mean,              
    name='平均值',
    marker_color='#34495e'
    ))
    fig.add_trace(go.Bar(
    x=city, 
    y=median,              
    name='中位数',
    marker_color='#16a085'
    ))
    fig.update_layout(
    title='不同城市的薪资对比',
    xaxis_tickfont_size=12,
    legend=dict(
        bordercolor='rgba(2, 255, 255, 0)'
    ),
    barmode='group',
    bargap=0.4,
    bargroupgap=0
    )
    py.offline.plot(fig,filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        csxz_chart = "".join(f.readlines())
    
    # 生成薪资在四千至六千的岗位数量图表
    薪资_四千至六千= new_df[(new_df['平均薪资']>4) & (new_df['平均薪资']<6)]
    薪资_四千至六千岗位数=pd.DataFrame(薪资_四千至六千.groupby('城市').平均薪资.count())
    new_df岗位数=薪资_四千至六千岗位数.reset_index().rename(columns={"平均薪资":"岗位数"})
    datas=pd.DataFrame({"岗位数量":new_df岗位数["岗位数"],"城市":new_df岗位数["城市"]})
    # 生成渐变色列表
    import plotly.colors as pc
    # 从蓝色到绿色的渐变
    color_list = pc.sequential.Blues[:len(datas)]
    fig=px.pie(datas,values="岗位数量",names="城市",title="薪资_四千至六千岗位数量的城市分布情况",template="seaborn",color_discrete_sequence=color_list)
    fig.update_traces(textposition="inside",textinfo="value+percent+label")
    py.offline.plot(fig, filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        xinzi46_chart = "".join(f.readlines())
    
    # 生成薪资小于八千的情况图表
    薪资小于八千= new_df[(new_df['平均薪资']<8)]
    薪资小于八千岗位数=pd.DataFrame(薪资小于八千.groupby('城市').平均薪资.count())
    new_df岗位数=薪资小于八千岗位数.reset_index().rename(columns={"平均薪资":"岗位数"})
    datas=pd.DataFrame({"岗位数量":new_df岗位数["岗位数"],"城市":new_df岗位数["城市"]})
    # 从绿色到青色的渐变
    color_list = pc.sequential.Greens[:len(datas)]
    fig=px.pie(datas,values="岗位数量",names="城市",title="薪资小于八千岗位数量的城市分布情况",template="seaborn",color_discrete_sequence=color_list)
    fig.update_traces(textposition="inside",textinfo="value+percent+label")
    py.offline.plot(fig, filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        xzxiao8_chart = "".join(f.readlines())
    
    # 生成薪资大于八千的情况图表
    薪资大于八千= new_df[(new_df['平均薪资']>8)]
    薪资大于八千岗位数=pd.DataFrame(薪资大于八千.groupby('城市').平均薪资.count())
    new_df岗位数=薪资大于八千岗位数.reset_index().rename(columns={"平均薪资":"岗位数"})
    datas=pd.DataFrame({"岗位数量":new_df岗位数["岗位数"],"城市":new_df岗位数["城市"]})
    # 从红色到橙色的渐变
    color_list = pc.sequential.Reds[:len(datas)]
    fig=px.pie(datas,values="岗位数量",names="城市",title="薪资大于八千岗位数量的城市分布情况",template="seaborn",color_discrete_sequence=color_list)
    fig.update_traces(textposition="inside",textinfo="value+percent+label")
    py.offline.plot(fig, filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        xzda8_chart = "".join(f.readlines())
    
    # 生成不同学历的薪资情况图表
    xueli=list(new_df.平均薪资.groupby(new_df['学历']).agg(['mean','median']).reset_index().iloc[:,0])
    mean=list(new_df.平均薪资.groupby(new_df['学历']).agg(['mean','median']).reset_index().iloc[:,1])
    median=list(new_df.平均薪资.groupby(new_df['学历']).agg(['mean','median']).reset_index().iloc[:,2])
    fig = go.Figure()
    fig.add_trace(go.Bar(
    x=xueli, 
    y=mean,              
    name='平均值',
    marker_color='#34495e'
    ))
    fig.add_trace(go.Bar(
    x=xueli, 
    y=median,              
    name='中位数',
    marker_color='#16a085'
    ))
    fig.update_layout(
    title='不同学历的薪资对比图',
    xaxis_tickfont_size=12,
    legend=dict(
        bordercolor='rgba(2, 255, 255, 0)'
    ),
    barmode='group',
    bargap=0.4,
    bargroupgap=0
    )
    py.offline.plot(fig, filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        xuelixz_chart = "".join(f.readlines())
    
    # 生成不同学历的岗位情况图表
    data2=pd.DataFrame(new_df.groupby('学历').职位.count())
    不同学历岗位数量=data2.reset_index().rename(columns={"职位":"岗位数"})
    datas=pd.DataFrame({"岗位数量":不同学历岗位数量["岗位数"],"学历":不同学历岗位数量["学历"]})
    # 从紫色到粉色的渐变
    import plotly.colors as pc
    color_list = pc.sequential.Purples[:len(datas)]
    fig=px.pie(datas,values="岗位数量",names="学历",title="不同学历岗位数量情况",template="seaborn",color_discrete_sequence=color_list)
    fig.update_traces(textposition="inside",textinfo="value+percent+label")
    py.offline.plot(fig, filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        xueligw_chart = "".join(f.readlines())
    
    # 生成不同工作经验的薪资情况图表
    工作经验=list(new_df.平均薪资.groupby(new_df['工作经验']).agg(['mean','median']).reset_index().iloc[:,0])
    mean=list(new_df.平均薪资.groupby(new_df['工作经验']).agg(['mean','median']).reset_index().iloc[:,1])
    median=list(new_df.平均薪资.groupby(new_df['工作经验']).agg(['mean','median']).reset_index().iloc[:,2])
    fig = go.Figure()
    fig.add_trace(go.Bar(
    x=工作经验, 
    y=mean,              
    name='平均值',
    marker_color='#34495e'
    ))
    fig.add_trace(go.Bar(
    x=工作经验, 
    y=median,              
    name='中位数',
    marker_color='#16a085'
    ))
    fig.update_layout(
    title='各工作年限薪资均值及中位数比较图',
    xaxis_tickfont_size=12,
    legend=dict(
        bordercolor='rgba(2, 255, 255, 0)'
    ),
    barmode='group',
    bargap=0.4,
    bargroupgap=0
    )
    py.offline.plot(fig, filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        gzjyxz_chart = "".join(f.readlines())
    
    # 生成不同工作经验的岗位情况图表
    new_df_工作经验=new_df[["工作经验","职位"]]
    new_df_gzjy=pd.DataFrame(new_df_工作经验.groupby('工作经验').职位.count())
    new_df_岗位数=new_df_gzjy.reset_index().rename(columns={"职位":"岗位数"})
    new_df_gzjy_s=pd.DataFrame({"工作经验":new_df_岗位数["工作经验"],"岗位数量":new_df_岗位数["岗位数"]})
    工作经验分析=new_df_gzjy_s.sort_values(by=["岗位数量"],ascending=False)
    fig=px.bar(工作经验分析,x="工作经验",y="岗位数量",color="工作经验",title="不同工作经验的岗位数量情况",template="seaborn")
    py.offline.plot(fig, filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        gzjygw_chart = "".join(f.readlines())
    
    # 生成不同行业的薪资情况图表
    hangye=list(new_df.平均薪资.groupby(new_df['行业标签']).agg(['mean','median']).reset_index().iloc[:,0])
    mean=list(new_df.平均薪资.groupby(new_df['行业标签']).agg(['mean','median']).reset_index().iloc[:,1])
    median=list(new_df.平均薪资.groupby(new_df['行业标签']).agg(['mean','median']).reset_index().iloc[:,2])
    fig = go.Figure()
    fig.add_trace(go.Bar(
    x=hangye, 
    y=mean,              
    name='平均值',
    marker_color='#34495e'
    ))
    fig.add_trace(go.Bar(
    x=hangye, 
    y=median,              
    name='中位数',
    marker_color='#16a085'
    ))
    fig.update_layout(
    title='不同行业的薪资对比图',
    xaxis_tickfont_size=14,
    legend=dict(
        bordercolor='rgba(2, 255, 255, 0)'
    ),
    barmode='group',
    bargap=0.4,
    bargroupgap=0
    )
    py.offline.plot(fig, filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        hyxz_chart = "".join(f.readlines())
    
    # 生成不同行业的岗位情况图表
    new_df_行业=new_df[["行业标签","职位"]]
    new_df_hybq=pd.DataFrame(new_df_行业.groupby('行业标签').职位.count())
    new_df_岗位数=new_df_hybq.reset_index().rename(columns={"职位":"岗位数"})
    new_df_hybq_s=pd.DataFrame({"行业":new_df_岗位数["行业标签"],"岗位数量":new_df_岗位数["岗位数"]})
    工作经验分析=new_df_hybq_s.sort_values(by=["岗位数量"],ascending=False)
    fig=px.bar(工作经验分析,x="行业",y="岗位数量",color="行业",title="不同行业的岗位数量情况",template="seaborn")
    py.offline.plot(fig, filename="example.html",auto_open=False)
    with open("example.html", encoding="utf8", mode="r") as f:
        hygw_chart = "".join(f.readlines())
    
    return render_template('dashboard.html',
                           csxz_chart=csxz_chart,
                           xinzi46_chart=xinzi46_chart,
                           xzxiao8_chart=xzxiao8_chart,
                           xzda8_chart=xzda8_chart,
                           xuelixz_chart=xuelixz_chart,
                           xueligw_chart=xueligw_chart,
                           gzjyxz_chart=gzjyxz_chart,
                           gzjygw_chart=gzjygw_chart,
                           hyxz_chart=hyxz_chart,
                           hygw_chart=hygw_chart)


if __name__ == '__main__':
    app.run(debug=True)