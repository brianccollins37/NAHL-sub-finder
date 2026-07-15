import React, { useState, useMemo } from 'react';
import { Phone, Mail, User, Calendar, ShieldAlert, CheckCircle2, AlertCircle, ShieldOff } from 'lucide-react';

// Scheduling rules: Track side games start on the hour/20/40. Road side games stagger by 10 mins.
const TIME_SLOTS = [
  { label: "8:00 PM (Track Side)", offset: 0 },
  { label: "8:10 PM (Road Side)", offset: 10 },
  { label: "9:20 PM (Track Side)", offset: 80 },
  { label: "9:30 PM (Road Side)", offset: 90 },
  { label: "10:40 PM (Track Side)", offset: 160 },
  { label: "10:50 PM (Road Side)", offset: 170 }
];

// Mock Data representing the Google Sheet
const MOCK_PLAYERS = [
  { id: 1, name: "Mike Smith", rating: 88, position: "Forward", team: "Lumberjacks", scheduleDate: "2026-06-25", scheduleTime: "8:00 PM (Track Side)", phone: "(412) 555-0101", email: "mike.s@example.com" },
  { id: 2, name: "David Jones", rating: 85, position: "Defense", team: "Ice Hogs", scheduleDate: "", scheduleTime: "Free", phone: "(412) 555-0102", email: "djones@example.com" },
  { id: 3, name: "Chris Wilson", rating: 82, position: "Forward", team: "Puck Hounds", scheduleDate: "2026-06-25", scheduleTime: "9:30 PM (Road Side)", phone: "(412) 555-0103", email: "cwilson@example.com" },
  { id: 4, name: "Tom Brown", rating: 79, position: "Defense", team: "Lumberjacks", scheduleDate: "2026-06-25", scheduleTime: "8:10 PM (Road Side)", phone: "(724) 555-0104", email: "tbrown_d@example.com" },
  { id: 5, name: "Dan Miller", rating: 92, position: "Goalie", team: "Iron Lungs", scheduleDate: "", scheduleTime: "Free", phone: "(724) 555-0105", email: "brickwall@example.com" },
  { id: 6, name: "Ryan Davis", rating: 84, position: "Forward", team: "Ice Hogs", scheduleDate: "2026-06-26", scheduleTime: "9:20 PM (Track Side)", phone: "(412) 555-0106", email: "rdavis@example.com" },
  { id: 7, name: "Kevin White", rating: 80, position: "Defense", team: "Puck Hounds", scheduleDate: "2026-06-25", scheduleTime: "10:40 PM (Track Side)", phone: "(412) 555-0107", email: "kwhite@example.com" },
  { id: 8, name: "Brian Clark", rating: 75, position: "Goalie", team: "Lumberjacks", scheduleDate: "2026-06-25", scheduleTime: "9:20 PM (Track Side)", phone: "(724) 555-0108", email: "bclark_net@example.com" },
  { id: 9, name: "Matt Taylor", rating: 86, position: "Forward", team: "Iron Lungs", scheduleDate: "2026-06-25", scheduleTime: "10:50 PM (Road Side)", phone: "(412) 555-0109", email: "mtaylor@example.com" },
  { id: 10, name: "Joe Anderson", rating: 81, position: "Forward", team: "Ice Hogs", scheduleDate: "", scheduleTime: "Free", phone: "(412) 555-0110", email: "janderson@example.com" },
  { id: 11, name: "Steve Thomas", rating: 89, position: "Defense", team: "Puck Hounds", scheduleDate: "2026-06-25", scheduleTime: "8:00 PM (Track Side)", phone: "(724) 555-0111", email: "sthomas@example.com" },
  { id: 12, name: "Alex Moore", rating: 77, position: "Forward", team: "Lumberjacks", scheduleDate: "2026-06-25", scheduleTime: "8:10 PM (Road Side)", phone: "(412) 555-0112", email: "amoore@example.com" },
  { id: 13, name: "Eric Jackson", rating: 83, position: "Defense", team: "Iron Lungs", scheduleDate: "2026-06-25", scheduleTime: "9:30 PM (Road Side)", phone: "(412) 555-0113", email: "ejackson@example.com" },
  { id: 14, name: "Adam Martin", rating: 85, position: "Goalie", team: "Ice Hogs", scheduleDate: "", scheduleTime: "Free", phone: "(724) 555-0114", email: "amartin@example.com" },
  { id: 15, name: "Scott Lee", rating: 78, position: "Forward", team: "Puck Hounds", scheduleDate: "", scheduleTime: "Free", phone: "(412) 555-0115", email: "slee@example.com" }
];

export default function App() {
  const [league, setLeague] = useState("NAHL");
  const [season, setSeason] = useState("Season 54");
  const [missingRating, setMissingRating] = useState(85);
  const [missingPosition, setMissingPosition] = useState("Skater");
  const [ourGameDate, setOurGameDate] = useState("2026-06-25");
  const [ourGameTime, setOurGameTime] = useState("9:20 PM (Track Side)");
  const [isPlayoffMode, setIsPlayoffMode] = useState(false);
  const [checkAvailability, setCheckAvailability] = useState(true);

  // Filter and process the roster
  const filteredRoster = useMemo(() => {
    return MOCK_PLAYERS.filter((player) => {
      // 1. Rating Logic
      const isEligibleRating = isPlayoffMode ? player.rating < missingRating : player.rating <= missingRating;
      if (!isEligibleRating) return false;

      // 2. Position Logic
      if (missingPosition === "Goalie") {
        if (player.position !== "Goalie") return false;
      } else {
        if (player.position === "Goalie") return false;
      }

      return true;
    }).map((player) => {
      // 3. Schedule Logic (Determine Status based on Time Offset)
      let status = "Free";
      let statusColor = "bg-green-100 text-green-800 border-green-200";
      let statusIcon = <CheckCircle2 className="w-4 h-4 mr-1 inline" />;

      if (!checkAvailability) {
        status = "Schedule Check Disabled";
        statusColor = "bg-slate-100 text-slate-600 border-slate-200";
        statusIcon = <ShieldOff className="w-4 h-4 mr-1 inline" />;
      } else if (player.scheduleTime !== "Free" && player.scheduleDate === ourGameDate) {
        const ourSlot = TIME_SLOTS.find(t => t.label === ourGameTime);
        const theirSlot = TIME_SLOTS.find(t => t.label === player.scheduleTime);

        if (ourSlot && theirSlot) {
          const diffMinutes = Math.abs(ourSlot.offset - theirSlot.offset);
          
          if (diffMinutes === 0) {
            status = "Unavailable (Conflict)";
            statusColor = "bg-red-100 text-red-800 border-red-200";
            statusIcon = <ShieldAlert className="w-4 h-4 mr-1 inline" />;
          } else if (diffMinutes <= 100) {
             // Game is adjacent (e.g. 8:00 and 9:20 or 8:10 and 9:30)
            status = `At Rink: ${player.scheduleTime}`;
            statusColor = "bg-amber-100 text-amber-800 border-amber-200";
            statusIcon = <AlertCircle className="w-4 h-4 mr-1 inline" />;
          } else {
             // Game is far apart (e.g. 8:00 and 10:40)
            status = `Playing at ${player.scheduleTime}`;
            statusColor = "bg-blue-100 text-blue-800 border-blue-200";
            statusIcon = <Calendar className="w-4 h-4 mr-1 inline" />;
          }
        }
      }

      return { ...player, status, statusColor, statusIcon };
    }).sort((a, b) => {
      // Sort Free/Disabled players to the top, then adjacent, then conflicts
      const priorityA = (a.status === "Free" || a.status === "Schedule Check Disabled") ? 1 : (a.status.includes("At Rink") ? 2 : 3);
      const priorityB = (b.status === "Free" || b.status === "Schedule Check Disabled") ? 1 : (b.status.includes("At Rink") ? 2 : 3);
      return priorityA - priorityB;
    });
  }, [missingRating, missingPosition, ourGameDate, ourGameTime, isPlayoffMode, checkAvailability]);

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="bg-slate-900 rounded-xl p-6 text-white shadow-lg flex flex-col md:flex-row justify-between items-start md:items-center">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Hockey Sub Finder</h1>
            <p className="text-slate-400 mt-1">Select a missing player to find eligible replacements.</p>
          </div>
          <div className="mt-4 md:mt-0 flex space-x-2">
            <select 
              value={league}
              onChange={(e) => setLeague(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="NAHL">NAHL (40+)</option>
              <option value="CVHL">CVHL (30+)</option>
              <option value="OFHL">OFHL (50+)</option>
            </select>
            <select 
              value={season}
              onChange={(e) => setSeason(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="Season 54">Season 54 (NAHL)</option>
              <option value="Season 53">Season 53 (NAHL)</option>
              <option value="Season 17">Season 17 (OFHL)</option>
            </select>
          </div>
        </div>

        {/* Configuration Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            
            {/* Missing Player Config */}
            <div className="space-y-4 col-span-1 md:col-span-2">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Missing Rating</label>
                <div className="flex items-center space-x-2">
                  <input 
                    type="range" 
                    min="40" 
                    max="110" 
                    value={missingRating}
                    onChange={(e) => setMissingRating(parseInt(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                  <span className="font-mono bg-slate-100 px-2 py-1 rounded text-slate-700 font-bold border border-slate-200">{missingRating}</span>
                </div>
              </div>

              <div>
                 <label className="block text-sm font-semibold text-slate-700 mb-1">Missing Position</label>
                 <select 
                    value={missingPosition}
                    onChange={(e) => setMissingPosition(e.target.value)}
                    className="w-full bg-white border border-slate-300 text-slate-900 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="Skater">Skater (F/D/E)</option>
                    <option value="Goalie">Goalie</option>
                  </select>
              </div>
            </div>

            {/* Game Context Config */}
            <div className="space-y-4 col-span-1 md:col-span-2 border-t md:border-t-0 md:border-l border-slate-200 pt-4 md:pt-0 md:pl-6">
               <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Our Game Date</label>
                <input 
                  type="date" 
                  value={ourGameDate}
                  onChange={(e) => setOurGameDate(e.target.value)}
                  className="w-full bg-white border border-slate-300 text-slate-900 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                 <label className="block text-sm font-semibold text-slate-700 mb-1">Our Game Time</label>
                 <select 
                    value={ourGameTime}
                    onChange={(e) => setOurGameTime(e.target.value)}
                    className="w-full bg-white border border-slate-300 text-slate-900 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {TIME_SLOTS.map(slot => (
                      <option key={slot.label} value={slot.label}>{slot.label}</option>
                    ))}
                  </select>
              </div>
            </div>

            {/* Toggles */}
            <div className="flex flex-col pt-2 justify-center space-y-4 col-span-1 border-t md:border-t-0 md:border-l border-slate-200 pt-4 md:pt-0 md:pl-6">
              <label className="flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={isPlayoffMode}
                  onChange={(e) => setIsPlayoffMode(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                <span className="ml-3 text-sm font-medium text-slate-700">Playoff Mode</span>
              </label>

              <label className="flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={checkAvailability}
                  onChange={(e) => setCheckAvailability(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-emerald-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
                <span className="ml-3 text-sm font-medium text-slate-700">Check Schedules</span>
              </label>
            </div>

          </div>
        </div>

        {/* Results Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
             <h2 className="text-lg font-semibold text-slate-800">Eligible Subs ({filteredRoster.length})</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-slate-50 text-slate-600 font-medium border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Player Name</th>
                  <th className="px-6 py-3">Team</th>
                  <th className="px-6 py-3">Rating</th>
                  <th className="px-6 py-3">Position</th>
                  <th className="px-6 py-3">Schedule Status</th>
                  <th className="px-6 py-3">Contact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRoster.length > 0 ? (
                  filteredRoster.map((player) => (
                    <tr 
                      key={player.id} 
                      className={`hover:bg-slate-50 transition-colors ${player.status === "Unavailable (Conflict)" ? "opacity-50" : ""}`}
                    >
                      <td className="px-6 py-4 font-medium text-slate-900 flex items-center">
                        <User className="w-4 h-4 text-slate-400 mr-2" />
                        {player.name}
                      </td>
                      <td className="px-6 py-4 text-slate-600 font-medium">{player.team}</td>
                      <td className="px-6 py-4">
                        <span className="bg-slate-100 text-slate-700 px-2 py-1 rounded font-mono text-xs border border-slate-200">
                          {player.rating}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-600">{player.position}</td>
                      <td className="px-6 py-4">
                         <span className={`px-2.5 py-1 rounded-full text-xs font-medium border flex items-center w-max ${player.statusColor}`}>
                            {player.statusIcon}
                            {player.statusText || player.status}
                         </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex space-x-2">
                           <a 
                             href={`sms:${player.phone.replace(/[^0-9]/g, '')}`}
                             className="text-slate-500 hover:text-blue-600 bg-slate-100 hover:bg-blue-50 p-1.5 rounded transition-colors"
                             title="Send Text"
                           >
                             <Phone className="w-4 h-4" />
                           </a>
                           <a 
                             href={`mailto:${player.email}`}
                             className="text-slate-500 hover:text-blue-600 bg-slate-100 hover:bg-blue-50 p-1.5 rounded transition-colors"
                             title="Send Email"
                           >
                             <Mail className="w-4 h-4" />
                           </a>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="6" className="px-6 py-8 text-center text-slate-500">
                      No eligible subs found for this rating and position.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
