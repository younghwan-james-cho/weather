
*Reset button;
/*
dm "out;clear;log;clear;";
proc delete data = _all_; run;
*/



libname test "C:\Users\ys1ha\Dropbox\Donghoon\4. Weather\Outputs";
data firm_char; set test.firm_char2; run;
proc sort data=firm_char nodupkey out=chk; by date; run;
data firm_char; set firm_char;
	date_a1m = intnx('month',date,1,'E');
	format date_a1m yymmddn8.;
	ME=size;
run;
proc sql; create table CRSPm
	as select a.*, b.retex as retex_a1
	from firm_char as a left join firm_char as b on a.permno=b.permno and a.date_a1m=b.date;
quit;
data CRSPm8; set CRSPm; 
	if 2005<=year(date)<=2024; 
	if abs(prc)<500 then delete; 
	if exch in ("유가증권시장", "코스닥");
	if ind_code="K" then delete;
run;




proc import datafile="D:\FNGuide\Data1\Factors_adj.xlsx"
	out = FF4_mnth
	dbms=xlsx
	replace;
run;
proc import out = risk_free
	datafile = "D:\FNGuide\Data1\risk_free.xlsx"
	dbms = xlsx replace;
	Sheet = 'Sheet3';
	getnames = yes;
run;
proc sql; create table FF4_mnth
	as select a.*, b.CD91, a.MKT-b.CD91 as MKT_rf
	from FF4_mnth as a left join Risk_free as b on a.date=b.date;
quit;

libname wthr "D:\DH_Weather";
data wther; set wthr.weather_grp10; non=1;run;












/* Table 2 */
/* Portfolio Alpha */

%macro portt(lg=);
%let ds_list=;

%do i =0 %to &grp_max;
	ods exclude all;
	proc model data=&tg._ret2;
	    instrument b0;
	    _&i = b0;
	    fit _&i / gmm kernel=(bart,&lg,);
		ods output parameterestimates = _&i;
	quit;
	ods exclude none;
	data _&i; set _&i; _Portfolio = "port_&i."; run;
	%let ds_list = &ds_list _&i;
%end;

ods exclude all;
proc model data=&tg._ret2;
    instrument b0;
    diff = b0;
    fit diff / gmm kernel=(bart,&lg,);
	ods output parameterestimates = diff;
quit;
ods exclude none;
data diff; set diff; _Portfolio = "diff"; run;
%let ds_list = &ds_list diff;




* CAPM;
%do i =0 %to &grp_max;
	ods exclude all;
	proc model data=&tg._ret2;
	    parms b0 b1;
	    _&i = b0 + b1*Mkt;
	    fit _&i / gmm kernel=(bart,&lg,);
		ods output parameterestimates = CAPM_&i;
	quit;
	ods exclude none;
	data CAPM_&i; set CAPM_&i; _Portfolio = "CAPM_&i."; if parameter="b0"; run;
	%let ds_list = &ds_list CAPM_&i;
%end;

ods exclude all;
proc model data=&tg._ret2;
    parms b0 b1;
    diff = b0 + b1*Mkt;
    fit diff / gmm kernel=(bart,&lg,);
	ods output parameterestimates = CAPM;
quit;
ods exclude none;
data CAPM; set CAPM; _Portfolio = "CAPM_diff"; if parameter="b0"; run;
%let ds_list = &ds_list CAPM;




* 3 Factor;
%do i =0 %to &grp_max;
	ods exclude all;
	proc model data=&tg._ret2;
	    parms b0 b1 b2 b3;
	    _&i = b0 + b1*Mkt + b2*SMB + b3*HML;
	    fit _&i / gmm kernel=(bart,&lg,);
		ods output parameterestimates = FF3_&i;
	quit;
	ods exclude none;
	data FF3_&i; set FF3_&i; _Portfolio = "FF3_&i."; if parameter="b0"; run;
	%let ds_list = &ds_list FF3_&i;
%end;

ods exclude all;
proc model data=&tg._ret2;
    parms b0 b1 b2 b3;
    diff = b0 + b1*Mkt + b2*SMB + b3*HML;
    fit diff / gmm kernel=(bart,&lg,);
	ods output parameterestimates = FF3;
quit;
ods exclude none;
data FF3; set FF3; _Portfolio = "FF3_diff"; if parameter="b0"; run;
%let ds_list = &ds_list FF3;





* 4 Factor;
%do i =0 %to &grp_max;
	ods exclude all;
	proc model data=&tg._ret2;
	    parms b0 b1 b2 b3 b4;
	    _&i = b0 + b1*Mkt + b2*SMB + b3*HML + b4*UMD;
	    fit _&i / gmm kernel=(bart,&lg,);
		ods output parameterestimates = FF4_&i;
	quit;
	ods exclude none;
	data FF4_&i; set FF4_&i; _Portfolio = "FF4_&i."; if parameter="b0"; run;
	%let ds_list = &ds_list FF4_&i;
%end;

ods exclude all;
proc model data=&tg._ret2;
    parms b0 b1 b2 b3 b4;
    diff = b0 + b1*Mkt + b2*SMB + b3*HML + b4*UMD;
    fit diff / gmm kernel=(bart,&lg,);
	ods output parameterestimates = FF4;
quit;
ods exclude none;
data FF4; set FF4; _Portfolio = "FF4_diff"; if parameter="b0"; run;
%let ds_list = &ds_list FF4;





* 5 Factor;
/*
%do i =0 %to &grp_max;
	ods exclude all;
	proc model data=&tg._ret2;
	    parms b0 b1 b2 b3 b4 b5;
	    _&i = b0 + b1*Mkt5 + b2*SMB5 + b3*HML5 + b4*RMW5 + b5*CMA5;
	    fit _&i / gmm kernel=(bart,&lg,);
		ods output parameterestimates = FF5_&i;
	quit;
	ods exclude none;
	data FF5_&i; set FF5_&i; _Portfolio = "FF5_&i."; if parameter="b0"; run;
	%let ds_list = &ds_list FF5_&i;
%end;

ods exclude all;
proc model data=&tg._ret2;
    parms b0 b1 b2 b3 b4 b5;
    diff = b0 + b1*Mkt5 + b2*SMB5 + b3*HML5 + b4*RMW5 + b5*CMA5;
    fit diff / gmm kernel=(bart,&lg,);
	ods output parameterestimates = FF5;
quit;
ods exclude none;
data FF5; set FF5; _Portfolio = "FF5_diff"; if parameter="b0"; run;
%let ds_list = &ds_list FF5;
*/
data Table2;
	set &ds_list;
run;
proc delete data=&ds_list; run;
%mend portt;






%let wth = non;
%let wtx = 1;

%macro T2_all(wth=, wtx=);
%let grp = 10;
%let grp_max = %eval(&grp-1);
%let tg  = Max1;
proc sort data=CRSPm8; by date; run;
proc rank data=CRSPm8 out=CRSPm9 groups=&grp;
	var &tg;
	by date;
	ranks &tg._rank;
run;

* Setting;
proc sort data=CRSPm9; by permno date; run;
proc sort data=CRSPm9; by &tg._rank date; run;
proc means data=CRSPm9 noprint;
	var retex_a1;
	by &tg._rank date;
	weight ME;
	where ME^=.;
	output out=&tg._ret(drop=_TYPE_ _FREQ_) mean=ret_a1;
run;
proc sort data=&tg._ret; by date &tg._rank; run;
proc transpose data=&tg._ret out=&tg._ret1;
	by date;
	ID &tg._rank;
run;
proc sql; create table &tg._ret2
	as select a.*, a._&grp_max - a._0 as diff, b.MKT_rf as Mkt, b.SMB as SMB, b.HML as HML, b.UMD as UMD
	from &tg._ret1 as a 
	left join FF4_mnth as b on intck('month',a.date,b.date)=1;
quit;
data &tg._ret2; set &tg._ret2; if diff^=.; if HML^=.; run;

proc sql; create table &tg._ret2
	as select a.*, b.*
	from &tg._ret2 as a left join wther as b on a.date=b.date;
quit;
data &tg._ret2; set &tg._ret2; if &wth in &wtx; run;
proc sort data=&tg._ret2; by date; run;

%portt(lg=12);



data Temp;
    set Table2; /* 원본 데이터셋 명칭 입력 */

	length model $10 label $15 col_name $10;
    /* 대소문자 구분 없이 비교하기 위해 소문자 변수 생성 */
    _p_name = lowcase(strip(_Portfolio));

    /* 1. _Portfolio 이름을 기준으로 모델명 지정 */
    if index(_p_name, 'port') > 0 or _p_name = 'diff' then model = "Raw";
    else if index(_p_name, 'capm') > 0 then model = "CAPM";
    else if index(_p_name, 'ff3') > 0 then model = "FF3";
    else if index(_p_name, 'ff4') > 0 then model = "FF4";

	last_part = lowcase(scan(_Portfolio, -1, '_')); 

    if last_part in ('diff', 'd', 'di') or index(lowcase(_Portfolio), 'diff') > 0 then 
        col_name = "diff";
    else do;
        /* 추출된 마지막 부분이 숫자라면 그 숫자만 사용 */
        /* FF3_0 에서 '0'만 추출하여 1을 더함 -> 1 */
        num_val = input(compress(last_part, , 'kd'), 8.);
        col_name = put(num_val + 1, 2. -l);
    end;

    label = "Estimate"; value = Estimate; output;
    label = "tvalue";   value = tValue;   output;

    keep model label col_name value;
run;

/* 2. 가로로 펼치기 위한 정렬 */
proc sort data=temp;
    by model label;
run;

/* 3. PROC TRANSPOSE를 사용하여 요청하신 구조로 변환 */
proc transpose data=temp out=temp2(drop=_name_);
    by model label;
    id col_name;
    var value;
run;

data Temp3;
    set Temp2;

    /* 모델 순서 지정 (Raw=1, CAPM=2, FF3=3, FF4=4) */
    length model $10;
    if model = "Raw" then mod_order = 1;
    else if model = "CAPM" then mod_order = 2;
    else if model = "FF3" then mod_order = 3;
    else if model = "FF4" then mod_order = 4;

    /* 라벨 순서 지정 (Estimate=1, tvalue=2) */
    if upcase(label) = "ESTIMATE" then lab_order = 1;
    else if upcase(label) = "TVALUE" then lab_order = 2;
run;

/* 2. 지정한 순서대로 정렬 */
proc sort data=Temp3;
    by mod_order lab_order;
run;
data Temp3; set Temp3;
	drop mod_order lab_order;
run;
%mend T2_all;
%T2_all(wth=non, wtx=(1));

/* 1. 데이터를 label(Estimate, tvalue) 순서대로 정렬 */
proc sort data=Temp3;
    by label;
run;

/* 2. 모든 모델의 diff 값만 따로 추출하여 가로(Wide form)로 변환 */
/* 이 과정을 거치면 diff_Raw, diff_CAPM, diff_FF3, diff_FF4 컬럼이 생깁니다 */
proc transpose data=Temp3 out=diff_transposed(drop=_name_) prefix=diff_;
    by label;
    id model;
    var diff;
run;

/* 3. Raw 모델의 기본 데이터(_1~_10)와 위에서 만든 diff 컬럼들을 합치기 */
data final_table;
    /* Raw 모델의 행에서 1~10번 포트폴리오 값만 가져옴 */
    merge temp3(where=(model='Raw') keep=model label _1-_10) 
          diff_transposed;
    by label;

    /* 4. 컬럼명 정리: 요구하신 이름 형식으로 변경 */
    rename diff_Raw  = diff
           diff_CAPM = capm_diff
           diff_FF3  = ff3_diff
           diff_FF4  = ff4_diff;

    /* 5. 컬럼 순서 고정 (원하시는 순서대로 배치) */
    retain label _1 _2 _3 _4 _5 _6 _7 _8 _9 _10 diff_Raw diff_CAPM diff_FF3 diff_FF4;
run;





*d_sun d_precip d_tempr d_cloud d_humd d_wind;
%macro T2_all2();
    /* 1. 세팅 리스트 정의 */
    %let wth_list = d_cloud d_sun d_precip d_tempr d_humd d_wind;
    /* wtx는 내부에 콤마가 있으므로 구분자를 |로 지정합니다 */
    %let wtx_list = %str((0,1,2))|%str((7,8,9))|%str((3,4,5,6));

    /* 2. 최종 결과 데이터셋 초기화 (기존 데이터 삭제) */
    proc datasets lib=work nolist;
        delete all_ds;
    quit;

    /* 3. 중첩 루프 시작 */
    /* wth 리스트 순회 */
    %do Tx1 = 1 %to %sysfunc(countw(&wth_list, %str( )));
        %let current_wth = %scan(&wth_list, &Tx1, %str( ));

        /* wtx 리스트 순회 (구분자 | 사용) */
        %do Tx2 = 1 %to %sysfunc(countw(&wtx_list, |));
            %let current_wtx = %scan(&wtx_list, &Tx2, |);

            /* A. 기존 매크로 실행 */
            %T2_all(wth=&current_wth, wtx=&current_wtx);

				/* 1. 데이터를 label(Estimate, tvalue) 순서대로 정렬 */
				proc sort data=Temp3; by label; run;
				/* 2. 모든 모델의 diff 값만 따로 추출하여 가로(Wide form)로 변환 */
				/* 이 과정을 거치면 diff_Raw, diff_CAPM, diff_FF3, diff_FF4 컬럼이 생깁니다 */
				proc transpose data=Temp3 out=diff_transposed(drop=_name_) prefix=diff_;
				    by label;
				    id model;
				    var diff;
				run;

				/* 3. Raw 모델의 기본 데이터(_1~_10)와 위에서 만든 diff 컬럼들을 합치기 */
				data temp4;
				    /* Raw 모델의 행에서 1~10번 포트폴리오 값만 가져옴 */
				    merge temp3(where=(model='Raw') keep=model label _1-_10) 
				          diff_transposed;
				    by label;

				    /* 4. 컬럼명 정리: 요구하신 이름 형식으로 변경 */
				    rename diff_Raw  = diff
				           diff_CAPM = capm_diff
				           diff_FF3  = ff3_diff
				           diff_FF4  = ff4_diff;

				    /* 5. 컬럼 순서 고정 (원하시는 순서대로 배치) */
				    retain label _1 _2 _3 _4 _5 _6 _7 _8 _9 _10 diff_Raw diff_CAPM diff_FF3 diff_FF4;
				run;




			/* B. 길이(Length)를 미리 지정하여 경고 방지 */
            data temp4_labeled;
                length wth_val $32 wtx_val $32; /* 충분한 길이를 미리 선언 */
                set temp4;
                wth_val = "&current_wth";
                wtx_val = "&current_wtx";
            run;

            /* C. all_ds 데이터셋에 누적 */
            proc append base=all_ds data=temp4_labeled force;
            run;
        %end;
    %end;
	data T2_port; set all_ds; run;
    proc delete data=temp4_labeled; run;
%mend T2_all2;
%T2_all2();
/*
proc export data=T2_port outfile="C:\Users\ys1ha\Dropbox\Donghoon\4. Weather\Outputs\Results\T2_port.xlsx"; run;
*/





/* Table 2-2. Subsample difference *//* Table 2-2. Subsample difference */
/* Table 2-2. Subsample difference *//* Table 2-2. Subsample difference */
/* Table 2-2. Subsample difference *//* Table 2-2. Subsample difference */
/* Table 2-2. Subsample difference *//* Table 2-2. Subsample difference */
/* Table 2-2. Subsample difference *//* Table 2-2. Subsample difference */
/* Table 2-2. Subsample difference *//* Table 2-2. Subsample difference */


%let wth = d_cloud;
%let wtx_1 = (0,1,2);
%let wtx_2 = (3,4,5,6);

%macro T2_wthr_diff(wth=, wtx_1=, wtx_2=, zx=12, outdd=);
%let ds_list=;
%let grp = 10;
%let grp_max = %eval(&grp-1);
%let tg  = Max1;
proc sort data=CRSPm8; by date; run;
proc rank data=CRSPm8 out=CRSPm9 groups=&grp;
	var &tg;
	by date;
	ranks &tg._rank;
run;

* Setting;
proc sort data=CRSPm9; by permno date; run;
proc sort data=CRSPm9; by &tg._rank date; run;
proc means data=CRSPm9 noprint;
	var retex_a1;
	by &tg._rank date;
	weight ME;
	where ME^=.;
	output out=&tg._ret(drop=_TYPE_ _FREQ_) mean=ret_a1;
run;
proc sort data=&tg._ret; by date &tg._rank; run;
proc transpose data=&tg._ret out=&tg._ret1;
	by date;
	ID &tg._rank;
run;
proc sql; create table &tg._ret2
	as select a.*, a._&grp_max - a._0 as diff, b.MKT_rf as Mkt, b.SMB as SMB, b.HML as HML, b.UMD as UMD
	from &tg._ret1 as a 
	left join FF4_mnth as b on intck('month',a.date,b.date)=1;
quit;
data &tg._ret2; set &tg._ret2; if diff^=.; if HML^=.; run;

proc sql; create table &tg._ret2
	as select a.*, b.*
	from &tg._ret2 as a left join wther as b on a.date=b.date;
quit;

data S22_1;
    set &tg._ret2;
    
    /* Sunny 그룹 정의: 0~2는 0(Low), 3~6은 1(High) */
    if &wth in &wtx_1 then dmy = 1;
    else if &wth in &wtx_2 then dmy = 0;
    else delete; /* 분석 대상 외 제외 */

    /* 상호작용 항 생성 (Mkt, SMB, HML이 더미에 따라 변하는지 확인용) */
    /* PROC MODEL 내에서 직접 계산도 가능하지만 미리 만들어두면 편리합니다. */
    mkt_d = Mkt * dmy;
    smb_d = SMB * dmy;
    hml_d = HML * dmy;
	umd_d = UMD * dmy;
run;







%do i =0 %to &grp_max;
	ods exclude all;
	proc model data=S22_1;
		parms a0 a1;
	    _&i = a0 + a1*dmy;
	    fit _&i / gmm kernel=(bart,&zx,);
		ods output parameterestimates = raw_&i;
	quit;
	ods exclude none;
	data raw_&i; set raw_&i; _Portfolio = "raw_&i."; if parameter="a1"; run;
	%let ds_list = &ds_list raw_&i;
%end;
ods exclude all;
proc model data=S22_1;
	parms a0 a1;
    diff = a0 + a1*dmy;
    fit diff / gmm kernel=(bart,&zx,);
	ods output parameterestimates = raw;
quit;
ods exclude none;
data raw; set raw; _Portfolio = "raw_diff"; if parameter="a1"; run;
%let ds_list = &ds_list raw;





%do i =0 %to &grp_max;
	ods exclude all;
	proc model data=S22_1;
		parms a0 b1 a1 d1;
	    _&i = a0 + b1*Mkt
	            + a1*dmy + d1*mkt_d;
	    fit _&i / gmm kernel=(bart,&zx,);
		ods output parameterestimates = capm_&i;
	quit;
	ods exclude none;
	data capm_&i; set capm_&i; _Portfolio = "capm_&i."; if parameter="a1"; run;
	%let ds_list = &ds_list capm_&i;
%end;
ods exclude all;
proc model data=S22_1;
	parms a0 b1 a1 d1;
    diff = a0 + b1*Mkt
            + a1*dmy + d1*mkt_d;
    fit diff / gmm kernel=(bart,&zx,);
	ods output parameterestimates = capm;
quit;
ods exclude none;
data capm; set capm; _Portfolio = "capm_diff"; if parameter="a1"; run;
%let ds_list = &ds_list capm;





%do i =0 %to &grp_max;
	ods exclude all;
	proc model data=S22_1;
		parms a0 b1 b2 b3 a1 d1 d2 d3;
	    _&i = a0 + b1*Mkt + b2*SMB + b3*HML 
	            + a1*dmy + d1*mkt_d + d2*smb_d + d3*hml_d;
	    fit _&i / gmm kernel=(bart,&zx,);
		ods output parameterestimates = FF3_&i;
	quit;
	ods exclude none;
	data FF3_&i; set FF3_&i; _Portfolio = "FF3_&i."; if parameter="a1"; run;
	%let ds_list = &ds_list FF3_&i;
%end;
ods exclude all;
proc model data=S22_1;
	parms a0 b1 b2 b3 a1 d1 d2 d3;
    diff = a0 + b1*Mkt + b2*SMB + b3*HML 
            + a1*dmy + d1*mkt_d + d2*smb_d + d3*hml_d;
    fit diff / gmm kernel=(bart,&zx,);
	ods output parameterestimates = FF3;
quit;
ods exclude none;
data FF3; set FF3; _Portfolio = "FF3_diff"; if parameter="a1"; run;
%let ds_list = &ds_list FF3;




%do i =0 %to &grp_max;
	ods exclude all;
	proc model data=S22_1;
		parms a0 b1 b2 b3 b4 a1 d1 d2 d3 d4;
	    _&i = a0 + b1*Mkt + b2*SMB + b3*HML + b4*UMD
	            + a1*dmy + d1*mkt_d + d2*smb_d + d3*hml_d + d4*UMD_d;
	    fit _&i / gmm kernel=(bart,&zx,);
		ods output parameterestimates = FF4_&i;
	quit;
	ods exclude none;
	data FF4_&i; set FF4_&i; _Portfolio = "FF4_&i."; if parameter="a1"; run;
	%let ds_list = &ds_list FF4_&i;
%end;
ods exclude all;
proc model data=S22_1;
	parms a0 b1 b2 b3 b4 a1 d1 d2 d3 d4;
    diff = a0 + b1*Mkt + b2*SMB + b3*HML + b4*UMD
            + a1*dmy + d1*mkt_d + d2*smb_d + d3*hml_d + d4*UMD_d;
    fit diff / gmm kernel=(bart,&zx,);
	ods output parameterestimates = FF4;
quit;
ods exclude none;
data FF4; set FF4; _Portfolio = "FF4_diff"; if parameter="a1"; run;
%let ds_list = &ds_list FF4;





data Tmp;
	length _portfolio $15; 
	set &ds_list;
run;
data Tmp; set Tmp;
	wth   = "&wth";
	wtx_1 = "&wtx_1";
	wtx_2 = "&wtx_2";
run;
proc delete data=&ds_list; run;


data Temp;
    set Tmp; /* 원본 데이터셋 명칭 입력 */

	length model $10 label $15 col_name $10;
    /* 대소문자 구분 없이 비교하기 위해 소문자 변수 생성 */
    _p_name = lowcase(strip(_Portfolio));

    /* 1. _Portfolio 이름을 기준으로 모델명 지정 */
    if index(_p_name, 'raw') > 0 or _p_name = 'diff' then model = "Raw";
    else if index(_p_name, 'capm') > 0 then model = "CAPM";
    else if index(_p_name, 'ff3') > 0 then model = "FF3";
    else if index(_p_name, 'ff4') > 0 then model = "FF4";

	last_part = lowcase(scan(_Portfolio, -1, '_')); 

    if last_part in ('diff', 'd', 'di') or index(lowcase(_Portfolio), 'diff') > 0 then 
        col_name = "diff";
    else do;
        /* 추출된 마지막 부분이 숫자라면 그 숫자만 사용 */
        /* FF3_0 에서 '0'만 추출하여 1을 더함 -> 1 */
        num_val = input(compress(last_part, , 'kd'), 8.);
        col_name = put(num_val + 1, 2. -l);
    end;

    label = "Estimate"; value = Estimate; output;
    label = "tvalue";   value = tValue;   output;

    keep model label col_name value wtx_1 wtx_2 wth;
run;

/* 2. 가로로 펼치기 위한 정렬 */
proc sort data=temp;
    by model label;
run;

/* 3. PROC TRANSPOSE를 사용하여 요청하신 구조로 변환 */
proc transpose data=temp out=temp2(drop=_name_);
    by model label;
    id col_name;
    var value;
run;

data Temp3;
    set Temp2;

    /* 모델 순서 지정 (Raw=1, CAPM=2, FF3=3, FF4=4) */
    length model $10;
    if model = "Raw" then mod_order = 1;
    else if model = "CAPM" then mod_order = 2;
    else if model = "FF3" then mod_order = 3;
    else if model = "FF4" then mod_order = 4;

    /* 라벨 순서 지정 (Estimate=1, tvalue=2) */
    if upcase(label) = "ESTIMATE" then lab_order = 1;
    else if upcase(label) = "TVALUE" then lab_order = 2;
run;

/* 2. 지정한 순서대로 정렬 */
proc sort data=Temp3;
    by mod_order lab_order;
run;
data Temp3; set Temp3;
	drop mod_order lab_order;
run;


/* 1. 데이터를 label(Estimate, tvalue) 순서대로 정렬 */
proc sort data=Temp3; by label; run;
/* 2. 모든 모델의 diff 값만 따로 추출하여 가로(Wide form)로 변환 */
/* 이 과정을 거치면 diff_Raw, diff_CAPM, diff_FF3, diff_FF4 컬럼이 생깁니다 */
proc transpose data=Temp3 out=diff_transposed(drop=_name_) prefix=diff_;
    by label;
    id model;
    var diff;
run;

/* 3. Raw 모델의 기본 데이터(_1~_10)와 위에서 만든 diff 컬럼들을 합치기 */
data temp4;
    /* Raw 모델의 행에서 1~10번 포트폴리오 값만 가져옴 */
    merge temp3(where=(model='Raw') keep=model label _1-_10) 
          diff_transposed;
    by label;

    /* 4. 컬럼명 정리: 요구하신 이름 형식으로 변경 */
    rename diff_Raw  = diff
           diff_CAPM = capm_diff
           diff_FF3  = ff3_diff
           diff_FF4  = ff4_diff;

    /* 5. 컬럼 순서 고정 (원하시는 순서대로 배치) */
    retain label _1 _2 _3 _4 _5 _6 _7 _8 _9 _10 diff_Raw diff_CAPM diff_FF3 diff_FF4;
run;




/* B. 길이(Length)를 미리 지정하여 경고 방지 */
data &outdd;
length wth_val $15 wtx_val $20; /* 충분한 길이를 미리 선언 */
set temp4;
wth_val = "&wth";
wtx_val = "&wtx_1._&wtx_2";
run;
%mend T2_wthr_diff;


%let wth = d_cloud;
%let wtx_1 = (0,1,2);
%let wtx_2 = (3,4,5,6);

%T2_wthr_diff(wth=d_cloud, wtx_1=(0,1,2), wtx_2=(3,4,5,6), zx=12, outdd=T22_1);



%macro T22_results();
	%let wth_list = d_cloud d_sun d_precip d_tempr d_humd d_wind;
    /* wtx는 내부에 콤마가 있으므로 구분자를 |로 지정합니다 */
    %let wtx_list = %str((0,1,2))|%str((7,8,9));
    /* 2. 최종 결과 데이터셋 초기화 (기존 데이터 삭제) */
    proc datasets lib=work nolist;
        delete all_ds;
    quit;

    /* 3. 중첩 루프 시작 */
    /* wth 리스트 순회 */
    %do Tx1 = 1 %to %sysfunc(countw(&wth_list, %str( )));
        %let current_wth = %scan(&wth_list, &Tx1, %str( ));

        /* wtx 리스트 순회 (구분자 | 사용) */
        %do Tx2 = 1 %to %sysfunc(countw(&wtx_list, |));
            %let current_wtx = %scan(&wtx_list, &Tx2, |);

            /* A. 기존 매크로 실행 */
			%T2_wthr_diff(wth=&current_wth, wtx_1=&current_wtx, wtx_2=(3,4,5,6), zx=12, outdd=T22_1);


            proc append base=all_ds data=T22_1 force;
            run;
        %end;
    %end;
	data T22_port; set all_ds; run;
%mend T22_results;
%T22_results();


data T2_port_final;
	set T2_port T22_port;
run;
%let wth_order = d_cloud d_sun d_precip d_tempr d_humd d_wind;
%let wtx_order = (0,1,2) (7,8,9) (3,4,5,6) (0,1,2)_(3,4,5,6) (7,8,9)_(3,4,5,6);

data sorted_data;
    set T2_port_final;

    /* 1. wth_rank: 리스트에서 몇 번째인지 찾기 */
    wth_rank = 0; /* 초기값 */
    %let n_wth = %sysfunc(countw(&wth_order., %str( ))); /* 매크로 수준에서 개수 파악 */
    
    do i = 1 to countw("&wth_order.", " "); 
        if strip(wth_val) = scan("&wth_order.", i, " ") then do;
            wth_rank = i;
            leave; /* 찾았으면 루프 종료 */
        end;
    end;

    /* 2. wtx_rank: 동일한 방식으로 처리 */
    wtx_rank = 0;
    do j = 1 to countw("&wtx_order.", " ");
        /* 구분자를 공백(" ")으로 지정하여 (0,1,2) 내부의 콤마 무시 */
        if strip(wtx_val) = scan("&wtx_order.", j, " ") then do;
            wtx_rank = j;
            leave;
        end;
    end;

    /* 3. label_rank 부여 */
    if upcase(strip(label)) = 'ESTIMATE' then label_rank = 1;
    else if upcase(strip(label)) = 'TVALUE' then label_rank = 2;

    drop i j;
run;
/* 3. 부여된 rank 변수들을 기준으로 정렬 */
proc sort data=sorted_data;
    by wth_rank wtx_rank label_rank;
run;

/* (선택사항) 정렬용으로 만든 임시 rank 변수 제거 */
data T2_portsort;
    set sorted_data;
    drop wth_rank wtx_rank label_rank;
run;

















/* 다른 파일에 있어서 따로 붙임. */

/* Table 3 */
/* Fama-MacBeth */
%let rtw = C:/Users/ys1ha/Dropbox/HK_Resch;
%include "&rtw/wrds/wrdsmacros/winsorize.sas";
%include "&rtw/wrds/wrdsmacros/nwords.sas";
data CRSPm9; set CRSPm8; Weight_l = ME; mom=mom12; rev=retex; run;
%WINSORIZE (INSET=CRSPm9, OUTSET=CRSPm10, SORTVAR=date, VARS= retex_a1 rev beta ME BM ROE AG retex mom max1 max5 illiq ivol ivol_12m, PERC1=1,TRIM=0);


data CRSPm10_cleans; set CRSPm10; 	log_size = log(ME); if year(date)<2025; 
    *if nmiss(retex_a1, ME, BM, IA, ROE, OP, mom, illiq, max, STd, ST, reg) = 0;
	str = rev;
run;

proc sql; create table CRSPm10_cleans
	as select a.*, b.*
	from CRSPm10_cleans as a left join wther as b on a.date=b.date;
quit;



%let wth=d_sun;
%let wtx=(1);
data CRSPm10_clean; set CRSPm10_cleans; if &wth in &wtx; run;
proc sort data=CRSPm10_clean; by date; run;


%macro FM_run(controls=, idx=);

 /* Step 1: Run cross-sectional regressions */
ods exclude all;
proc reg data=CRSPm10_clean outest=coef noprint;
    by date;
    model retex_a1 = &controls;
	*weight weight_l;
run;
ods exclude none;
data coef; set coef; if _RMSE_=. then delete; run;


 /* Step 3: Loop through each control variable for GMM test */
%let t_val_result=;
%let nvars = %sysfunc(countw(&controls));

%do i=1 %to &nvars;
	%let tgt=%scan(&controls, &i);
	ods exclude all;
	proc model data=coef;
	    instrument b0;
	    &tgt = b0;
	    fit &tgt / gmm kernel=(bart,4,);
		ods output parameterestimates = T_val_&i;
	quit;
	ods exclude none;

	data T_val_&i; 
		set T_val_&i;
		_NAME_="&tgt.";
	run;
%let t_val_result = &t_val_result T_val_&i;
%end;


data T4_line;
	length _NAME_ $10;
    set &t_val_result;
run;
data Esti; set T4_line;
	model_&idx  = estimate;
	_Type_		= "Estimate";
	keep _NAME_  _Type_ model_&idx;
run;
data T_val; set T4_line;
	model_&idx  = tValue;
	_Type_		= "Tvalue";
	keep _NAME_  _Type_ model_&idx;
run;

data T4_&idx; set Esti T_val; run;
proc delete data=&t_val_result T4_line Esti T_val; run;
proc sort data=T4_&idx; by _NAME_; run;
%mend FM_run;


%FM_run(controls=Max1, idx=1);
%FM_run(controls=Max1 beta log_size BM ROE, idx=2);
%FM_run(controls=Max1 beta log_size BM ROE retex, idx=3);
%FM_run(controls=Max1 beta log_size BM ROE retex mom, idx=4);
%FM_run(controls=Max1 beta log_size BM ROE retex mom illiq, idx=5);
%FM_run(controls=Max1 beta log_size BM ROE retex mom illiq ivol_12m, idx=6);


data Table4_FM;
	merge T4_1 T4_2 T4_3 T4_4 T4_5 T4_6;
	by _NAME_ _TYPE_;
run;
data Table4_FM; set Table4_FM;
	Num = .;
	if _NAME_="Max1" 		then Num=1;
	if _NAME_="beta" 		then Num=2;
	if _NAME_="log_size" 	then Num=3;
	if _NAME_="BM" 			then Num=4;
	if _NAME_="ROE" 		then Num=5;
	if _NAME_="IA" 			then Num=6;
	if _NAME_="retex" 		then Num=7;
	if _NAME_="mom" 		then Num=8;
	if _NAME_="illiq" 		then Num=9;
	if _NAME_="ivol" 		then Num=10;
	if _NAME_="ivol_12m" 		then Num=10;
run;
data Table4_FM; retain _NAME_ _TYPE_ Num; set Table4_FM; run;
proc sort data=Table4_FM; by Num _TYPE_; run;
