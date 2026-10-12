BEGIN {
 n=200000; maxroot=0; maxtrig=0; maxlog=0; sum=0;
 for(i=1;i<=n;i++) {
  x=i/1024.0;
  r=sqrt(x); e=r*r-x; if(e<0)e=-e; if(e>maxroot)maxroot=e;
  a=sin(x); b=cos(x); e=a*a+b*b-1; if(e<0)e=-e; if(e>maxtrig)maxtrig=e;
  e=exp(log(1+x))-(1+x); if(e<0)e=-e; if(e>maxlog)maxlog=e;
  sum+=a*a+b*b;
 }
 printf("%d %.17g %.17g %.17g %.17g\n",n,maxroot,maxtrig,maxlog,sum);
 if(maxroot>1e-9 || maxtrig>1e-12 || maxlog>1e-9 || sum<n-1e-5 || sum>n+1e-5)exit 3;
}
