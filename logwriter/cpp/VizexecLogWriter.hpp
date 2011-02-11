/**
 * @file  VizexecLogWriter.hpp
 * @brief VizEXEC用ログライター
 *
 * @author Sunagae
 * @date 2011-02-11
 * 
 * VizEXECで視覚化するためのログライター
 * 視覚化したい部分に適当なマーカーマクロを書き込むことで、その部分の視覚化をすることができる。
 * 詳細は各マクロの説明を。
 * 
 * ログの書き込み処理はスレッド化されているので、性能に対するオーバーヘッドはそんなにないはず。。。
 * 
 */

#ifndef VIZEXEC_LOGWRITER_HPP_
#define VIZEXEC_LOGWRITER_HPP_

#include <string>
#include <boost/thread.hpp>


#ifdef ENABLE_VIZEXEC
/// ロギングの開始を指示する。他のVZE_***マクロを使用する前に必ず呼び出す
#	define VZE_START \
		vizexec::EnableLogWriter();
/// シーケンス図に出力する関数マーカー
#	define VZE_FUNC 	\
		vizexec::func_tracer __vzp_tracer(__func__);
/// シーケンス図に出力する関数マーカー（別名を使用）
#	define VZE_FUNCCUSTOM(name) \
		vizexec::func_tracer __vzp_tracer(name);
/// フェーズマーカー
#	define VZE_PHASE(name) \
		vizexec::WritePhase(name);
/// メッセージ送信マーカー
#	define VZE_SEND1(ptr)		\
		vizexec::WriteSend(vizexec::get_ptr(ptr));
/// メッセージ受信マーカー
#	define VZE_RECV1(ptr)		\
		vizexec::WriteRecv(vizexec::get_ptr(ptr));
/// メッセージ送信マーカー (2 params)
#	define VZE_SEND2(p1, p2)		\
		vizexec::WriteSend(vizexec::get_ptr(p1), vizexec::get_ptr(p2));
/// メッセージ受信マーカー (2 params)
#	define VZE_RECV2(p1, p2)		\
		vizexec::WriteRecv(vizexec::get_ptr(p1), vizexec::get_ptr(p2));
/// イベントマーカー
#	define VZE_EVENT(str)		\
		vizexec::WriteEvent(str);

/// スレッド名マーカー
#	define VZE_THREADNAME(name)		\
		vizexec::SetCurrentThreadName(name);

#else
#   define VZE_START
#	define VZE_FUNC
#	define VZE_FUNCCUSTOM(name)
#	define VZE_PHASE(name)
#	define VZE_SEND1(ptr)
#	define VZE_RECV1(ptr)
#	define VZE_RECV2(p1,p2)
#	define VZE_SEND2(p1,p2)
#   define VZE_EVENT(str)
#   define VZE_THREADNAME(name)
#endif


namespace vizexec
{
using std::string;
typedef unsigned long long trace_time_t;

class func_tracer
{
	const char *func_name_;
public:
	func_tracer(const char *func);
	~func_tracer();
};


template<typename T>
inline const void* get_ptr(T* value)
{
	return value;
}

inline const void* get_ptr(int value)
{
    return *((void **)&value);
}


// for Smart pointers
/*
template<typename T>
inline void* get_ptr(shared_ptr<T> value)
{
	return value.get();
}
*/

int GetCurrentThreadID();
void SetCurrentThreadName(const string &name);

void EnableLogWriter();
bool IsLogWriterEnabled();

void WriteRecv(const void *p1, const void *p2 = NULL);
void WriteSend(const void *p1, const void *p2 = NULL);
void WriteComment(const string &comment);
void WriteEvent(const string &comment);
void WritePhase(const char *phase_name);

}



#endif /* VIZEXEC_LOGWRITER_HPP_ */
