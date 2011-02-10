/**
 * @file  Sample.cpp
 * @brief VizexecLogWriterの使用サンプル
 *
 * @author Sunagae
 * @date 2011-02-11
 */

// VizexecLogWriterを有効化するためにはENABLE_VIZEXECマクロを定義する。
// これを定義しないと、VZE_***マクロはすべて無視される
#define ENABLE_VIZEXEC

#include <string>
#include <iostream>
#include <cstdlib>
#include <boost/thread.hpp>
#include "VizexecLogWriter.hpp"

using namespace std;
using namespace boost;

const char *gMessageBuf = NULL;
const char *gAckBuf = NULL;
thread gProcessThread;

#define ms_sleep(t)     usleep((t) * 1000)

//------------------------------------------------------------------------------
// Functions for ProcessThread
//------------------------------------------------------------------------------
const char *WaitForMessage()
{
    VZE_FUNC
    while(!gMessageBuf)
        ms_sleep(1000);
    VZE_RECV1(gMessageBuf)
    return gMessageBuf;
}

const char *ProcessMessage(const char *msg)
{
    VZE_FUNC
    ms_sleep(1000);
    VZE_EVENT("MessageProcessEvent")
    // do something
    ms_sleep(2000);
    return "<ackmessage>";
}

void SendAck(const char *msg)
{
    VZE_FUNC
    VZE_SEND1(msg)
    gAckBuf = msg;
}

void process_thread()
{
    VZE_FUNCCUSTOM("ThreadMain")
    VZE_THREADNAME("ProcessThread")
    while(true)
    {
        const char *msg = WaitForMessage();
        VZE_PHASE("Process phase")
        const char *result = ProcessMessage(msg);
        SendAck(result);
    }
}

//------------------------------------------------------------------------------
// Functions for MainThread
//------------------------------------------------------------------------------
void CreateThread()
{
    VZE_FUNC
    gProcessThread = thread(&process_thread);
    ms_sleep(1000);
}


void SendMessage(const char *msg)
{
    VZE_FUNC
    VZE_SEND1(msg)
    gMessageBuf = msg;
}

const char* WaitForAck()
{
    VZE_FUNC
    while(!gAckBuf)
        ms_sleep(1000);
    VZE_RECV1(gAckBuf)
    return gAckBuf;    
}

void ShowResult(const char *result)
{
    VZE_FUNC
    cout << "Result: " << result << endl;
    VZE_EVENT("DrawEvent")
}

int main()
{
    VZE_START
    VZE_THREADNAME("MainThread")
    VZE_FUNC
    CreateThread();
    SendMessage("testmessage");
    const char *result = WaitForAck();
    ShowResult(result);

}
